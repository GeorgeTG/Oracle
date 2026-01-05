# Oracle/services/service_base.py

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Union, TYPE_CHECKING

from Oracle.parsing.parsers.events import ParserEvent
from Oracle.parsing.parsers.events.parser_event_type import ParserEventType
from Oracle.parsing.parsers.events.player_join import PlayerJoinEvent
from Oracle.services.event_bus import EventBus, Event, EventType
from Oracle.services.events.service_event import ServiceEvent, ServiceEventType
from Oracle.services.events.session_events import SessionRestoreEvent, SessionStartedEvent, SessionFinishedEvent, PlayerChangedEvent

if TYPE_CHECKING:
    from Oracle.database.models import Player, Session
else:
    from Oracle.database.models import Player, Session


class ServiceBase(ABC):
    """
    A service consumes both ParserEvents and ServiceEvents via EventBus.
    Automatically tracks current player and session.
    """
    _event_bus: EventBus
    _current_player_name: Optional[str]
    _current_session_id: Optional[int]

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._current_player_name = None
        self._current_session_id = None
        # Note: _register methods are now async, call them after construction
        self._initialized = False
    
    async def initialize(self):
        """Initialize event handlers (must be called after construction)."""
        if not self._initialized:
            await self._register_event_handlers()
            await self._register_base_handlers()
            self._initialized = True

    async def _register_base_handlers(self):
        """Register base class handlers for player and session tracking."""
        await self._event_bus.subscribe(self._on_session_started_base, ServiceEventType.SESSION_STARTED)
        await self._event_bus.subscribe(self._on_session_finished_base, ServiceEventType.SESSION_FINISHED)
        await self._event_bus.subscribe(self._on_session_restored_base, ServiceEventType.SESSION_RESTORE)

    async def _register_event_handlers(self):
        """Auto-register methods decorated with @event_handler to the event bus."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            # Support both old and new decorator attribute names
            if hasattr(attr, '_event_types'):
                for event_type in attr._event_types:
                    await self._event_bus.subscribe(attr, event_type)
            elif hasattr(attr, '_service_event_types'):
                # Backward compatibility
                for event_type in attr._service_event_types:
                    await self._event_bus.subscribe(attr, event_type)

    async def _on_player_join_base(self, event: PlayerJoinEvent):
        """Base handler for player join events."""
        # Check if player is changing or it's the first player
        if self._current_player_name != event.player_name:
            # Fire player changed event (old_player=None for first player)
            player_changed_event = PlayerChangedEvent(
                timestamp=datetime.now(),
                old_player=self._current_player_name,  # None on first player
                new_player=event.player_name
            )
            await self.publish(player_changed_event)
        
        self._current_player_name = event.player_name

    async def _on_session_started_base(self, event: SessionStartedEvent):
        """Base handler for session started events."""
        self._current_session_id = event.session_id
        self._current_player_name = event.player_name

    async def _on_session_finished_base(self, event: SessionFinishedEvent):
        """Base handler for session finished events."""
        self._current_session_id = None

    async def _on_session_restored_base(self, event: SessionRestoreEvent):
        """Base handler for session restore events."""
        self._current_session_id = event.session_id
        self._current_player_name = event.player_name

    def get_player_name(self) -> Optional[str]:
        """Get the current player name."""
        return self._current_player_name

    def get_session_id(self) -> Optional[int]:
        """Get the current session ID."""
        return self._current_session_id

    async def get_player(self, name: Optional[str] = None) -> Optional['Player']:
        """Get or create a player from database.
        
        Args:
            name: Player name to get/create. If None, uses current tracked player name.
            
        Returns:
            Player object if found/created, None if no name provided.
        """
        player_name = name or self._current_player_name
        if not player_name:
            return None
        
        # Get or create player (handle race condition with try/except)
        player = await Player.get_or_none(name=player_name)
        if not player:
            try:
                player = await Player.create(name=player_name)
            except Exception:
                # Race condition: player was created between get_or_none and create
                # Try to fetch again
                player = await Player.get_or_none(name=player_name)
                if not player:
                    raise
        
        # Update last_seen timestamp
        player.last_seen = datetime.now()
        await player.save()
        
        return player

    async def get_session(self) -> Optional['Session']:
        """Get the current session from database."""
        if not self._current_session_id:
            return None
        
        return await Session.get_or_none(id=self._current_session_id)

    async def publish(self, event: Event):
        """Publish an event (ServiceEvent or ParserEvent) to the event bus."""
        await self._event_bus.publish(event)

    async def wait_for_event(self, event_type: EventType, timeout: Optional[float] = None) -> Optional[Event]:
        """
        Wait for a specific event type to be published.
        
        Args:
            event_type: The type of event to wait for
            timeout: Maximum time to wait in seconds (None = wait indefinitely)
            
        Returns:
            The event if received within timeout, None if timeout occurred
        """
        event_future = asyncio.Future()
        
        async def event_handler(event: Event):
            if not event_future.done():
                event_future.set_result(event)
        
        # Subscribe to the event
        await self._event_bus.subscribe(event_handler, event_type)
        
        try:
            if timeout is not None:
                result = await asyncio.wait_for(event_future, timeout=timeout)
            else:
                result = await event_future
            return result
        except asyncio.TimeoutError:
            return None
        finally:
            # Unsubscribe after receiving the event or timeout
            await self._event_bus.unsubscribe(event_handler, event_type)

    async def request_and_wait(self, publish_event: Event, wait_event_type: EventType, timeout: Optional[float] = None) -> Optional[Event]:
        """
        Publish an event and wait for a response of a specific type.
        
        Args:
            publish_event: The event to publish (typically a request event)
            wait_event_type: The type of event to wait for (typically a response event)
            timeout: Maximum time to wait in seconds (None = wait indefinitely)
            
        Returns:
            The response event if received within timeout, None if timeout occurred
        """
        # Start waiting first to avoid race conditions
        wait_task = asyncio.create_task(self.wait_for_event(wait_event_type, timeout=timeout))
        
        # Small delay to ensure subscription is registered
        await asyncio.sleep(0)
        
        # Publish the request
        await self.publish(publish_event)
        
        # Wait for the response
        return await wait_task

    @abstractmethod
    async def startup(self):
        """Initialize service resources. Called during service initialization."""
        pass

    @abstractmethod
    async def shutdown(self):
        """Cleanup service resources. Called during service shutdown."""
        pass

    async def post_startup(self):
        """Hook called after all services have been started."""
        pass
