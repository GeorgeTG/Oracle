from datetime import datetime
from typing import Optional

from Oracle.database.models import Session, Player

from Oracle.parsing.parsers.events import ParserEventType
from Oracle.parsing.parsers.events.player_join import PlayerJoinEvent
from Oracle.parsing.parsers.events.game_view import GameViewEvent

from Oracle.events import EventBus
from Oracle.services.events.service_event import ServiceEventType
from Oracle.services.events.session_events import SessionControlEvent, SessionControlAction, SessionStartedEvent, SessionFinishedEvent, SessionSnapshotEvent, PlayerChangedEvent
from Oracle.services.events.stats_events import StatsUpdateEvent
from Oracle.services.events.notification_events import NotificationEvent, NotificationSeverity
from Oracle.services.service_base import ServiceBase
from Oracle.services.tooling.decorators import event_handler

from Oracle.tooling.logger import Logger


logger = Logger("SessionService")


class SessionService(ServiceBase):
    """Service that manages farming sessions."""
    
    __SERVICE__ = {
        "name": "SessionService",
        "version": "0.0.1",
        "description": "Manages farming sessions with statistics tracking",
        "requires": {}
    }

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        
        self._current_session: Optional[Session] = None
        
        logger.info("📋 SessionService initialized")
    
    async def startup(self):
        """Start the session service."""
        logger.info("📋 SessionService started")
    
    async def post_startup(self):
        """Initialize the service and clean up any active sessions."""
        # Check for existing active session first
        existing_session = await Session.filter(is_active=True).first()
        
        if existing_session:
            logger.info(f"📋 Found active session {existing_session.id}, restoring...")
            self._current_session = existing_session
            
            # Publish SessionRestoreEvent to notify other services
            from Oracle.services.events.session_events import SessionRestoreEvent
            restore_event = SessionRestoreEvent(
                timestamp=datetime.now(),
                session_id=existing_session.id,
                player_name=existing_session.player_name or "Unknown",
                started_at=existing_session.started_at,
                total_maps=existing_session.total_maps,
                total_time=existing_session.total_time,
                currency_total=existing_session.currency_total,
                currency_per_hour=existing_session.currency_per_hour,
                currency_per_map=existing_session.currency_per_map,
                exp_total=existing_session.exp_total,
                exp_per_hour=existing_session.exp_per_hour
            )
            await self.publish(restore_event)
            logger.info(f"📋 Published session restore event for session {existing_session.id}")
        else:
            logger.info("📋 No active session found, ready to start new session")

    async def start_session(self, player_name: Optional[str] = None) -> Session:
        """Start a new farming session."""
        logger.debug(f"📋 Starting new session for player: {player_name or 'Unknown'}")
        if not player_name:
            logger.info("📋 No player name provided, aborting session start")
            return None

        # Close existing session if any
        if self._current_session:
            await self.close_session()
        
        # Get or create player
        player, created = await Player.get_or_create(name=player_name)
        
        # Create new session
        self._current_session = await Session.create(
            player=player,
            player_name=player_name,
            started_at=datetime.now(),
            is_active=True
        )
        
        # Publish session started event
        started_event = SessionStartedEvent(
            timestamp=datetime.now(),
            session_id=self._current_session.id,
            player_name=player_name,
            started_at=self._current_session.started_at,
            description=self._current_session.description
        )
        await self.publish(started_event)
        
        logger.info(f"📋 Started new session {self._current_session.id} for player: {player_name or 'Unknown'}")
        return self._current_session

    async def close_session(self) -> Optional[Session]:
        """Close the current farming session."""
        if not self._current_session:
            logger.warning("📋 No active session to close")
            return None
        
        # Update session end time and mark as inactive
        self._current_session.ended_at = datetime.now()
        self._current_session.is_active = False
        await self._current_session.save()
        
        # Publish session finished event
        finished_event = SessionFinishedEvent(
            timestamp=datetime.now(),
            session_id=self._current_session.id,
            player_name=self._current_session.player_name or "Unknown",
            started_at=self._current_session.started_at,
            ended_at=self._current_session.ended_at,
            total_maps=self._current_session.total_maps,
            total_currency_delta=self._current_session.total_currency_delta,
            currency_per_hour=self._current_session.currency_per_hour,
            currency_per_map=self._current_session.currency_per_map,
            description=self._current_session.description
        )
        await self.publish(finished_event)
        
        logger.info(
            f"📋 Closed session {self._current_session.id} - "
            f"Maps: {self._current_session.total_maps}, "
            f"Currency: {self._current_session.total_currency_delta:.2f}, "
            f"Currency/hr: {self._current_session.currency_per_hour:.2f}"
        )
        
        closed_session = self._current_session
        self._current_session = None
        
        return closed_session

    @event_handler(ServiceEventType.STATS_UPDATE)
    async def on_stats_update(self, event: StatsUpdateEvent):
        """Update current session with latest statistics."""
        if not self._current_session:
            # Auto-start session only if we have a valid player name
            player_name = self.get_player_name()
            if player_name:
                await self.start_session(player_name)
            else:
                logger.debug("📋 Skipping session start - no player name available yet")
                return
        
        # Double-check session exists after potential auto-start
        if not self._current_session:
            logger.debug("📋 No active session to update with stats")
            return
            
        # Update session statistics
        self._current_session.total_maps = event.total_maps
        self._current_session.total_currency_delta = event.currency_per_map * event.total_maps
        self._current_session.currency_per_hour = event.currency_per_hour
        self._current_session.currency_per_map = event.currency_per_map
        
        # Save stats service state for restore
        self._current_session.total_time = event.total_time
        self._current_session.exp_total = event.exp_per_hour  # Store current exp/hour as proxy for total
        self._current_session.exp_per_hour = event.exp_per_hour
        self._current_session.currency_total = event.currency_total
        
        await self._current_session.save()
        
        logger.debug(f"📋 Updated session {self._current_session.id} with latest stats")

    @event_handler(ServiceEventType.SESSION_CONTROL)
    async def on_session_control(self, event: SessionControlEvent):
        """Handle session control events."""
        logger.info(f"📋 Session control action: {event.action}")
        
        if event.action == SessionControlAction.START:
            # Use event player name if provided, otherwise use cached player name
            player_name = event.player_name or self.get_player_name()
            await self.start_session(player_name)
        elif event.action == SessionControlAction.CLOSE:
            await self.close_session()
        elif event.action == SessionControlAction.NEXT:
            # Atomically close current and start new session
            await self.close_session()
            # Use event player name if provided, otherwise use cached player name
            player_name = event.player_name or self.get_player_name()
            await self.start_session(player_name)

    def get_current_session(self) -> Optional[Session]:
        """Get the current active session."""
        return self._current_session

    @event_handler(ParserEventType.PLAYER_JOIN)
    async def on_player_join(self, event: PlayerJoinEvent):
        """Handle player join - publish PLAYER_CHANGED if player changed."""
        # Check if player is changing or it's the first player
        if self._current_player_name != event.player_name:
            # Fire player changed event (old_player=None for first player)
            player_changed_event = PlayerChangedEvent(
                timestamp=datetime.now(),
                old_player=self._current_player_name,  # None on first player
                new_player=event.player_name
            )
            await self.publish(player_changed_event)
        
        # Update tracked player name
        self._current_player_name = event.player_name
        
        # Check if there's an active session in database for this player
        active_session = await Session.filter(is_active=True, player_name=event.player_name).first()
        
        # Only send restore event if:
        # 1. There is an active session in DB
        # 2. We don't already have it loaded (different session_id or no current session)
        if active_session and (not self._current_session or self._current_session.id != active_session.id):
            logger.info(f"📋 Found different active session in DB (id={active_session.id}), restoring...")
            
            # Update current session reference
            self._current_session = active_session
            
            # Send restore event to UI
            from Oracle.services.events.session_events import SessionRestoreEvent
            restore_event = SessionRestoreEvent(
                timestamp=datetime.now(),
                session_id=active_session.id,
                player_name=active_session.player_name or "Unknown",
                started_at=active_session.started_at,
                total_maps=active_session.total_maps,
                total_time=active_session.total_time,
                currency_total=active_session.currency_total,
                currency_per_hour=active_session.currency_per_hour,
                currency_per_map=active_session.currency_per_map,
                exp_total=active_session.exp_total,
                exp_per_hour=active_session.exp_per_hour
            )
            await self.publish(restore_event)
            logger.info(f"📋 Published session restore event on player join for session {active_session.id}")
        elif self._current_session and active_session and self._current_session.id == active_session.id:
            logger.debug(f"📋 Active session {self._current_session.id} already loaded, skipping restore event")

    @event_handler(ServiceEventType.PLAYER_CHANGED)
    async def on_player_changed(self, event: PlayerChangedEvent):
        """Handle player change - close current session and start new one for new player."""
        logger.info(f"📋 Player changed: {event.old_player} → {event.new_player}")
        
        # Close current session if exists
        if self._current_session:
            await self.close_session()
        
        # Start new session for new player
        await self.start_session(event.new_player)

    @event_handler(ServiceEventType.REQUEST_SESSION)
    async def on_request_session(self, event):
        """Handle REQUEST_SESSION event by publishing SESSION_SNAPSHOT."""
        from Oracle.services.events.session_events import SessionSnapshotEvent
        
        snapshot = SessionSnapshotEvent(
            timestamp=datetime.now(),
            session_id=self._current_session.id if self._current_session else None,
            player_name=self.get_player_name(),
            started_at=self._current_session.started_at if self._current_session else None,
            is_active=self._current_session is not None
        )
        await self.publish(snapshot)
        logger.debug(f"📋 Published session snapshot: session_id={snapshot.session_id}, active={snapshot.is_active}")

    async def shutdown(self):
        """Shutdown session service - keep active session for restore on next startup."""
        logger.info("📋 SessionService shutdown - preserving active session for restore")
        # Note: We intentionally do NOT close active sessions here
        # They will be restored on next startup via SessionRestoreEvent

    @event_handler(ParserEventType.GAME_VIEW)
    async def on_game_view(self, event: GameViewEvent):
        """Handle game view changes - check for active sessions on Login screen."""
        # Check if we're on the login screen
        if "Login" in event.view:
            logger.info("📋 Login screen detected, checking for active sessions...")
            
            # Search for any active session in database
            active_session = await Session.filter(is_active=True).first()
            
            if active_session:
                # Send notification to UI about existing active session
                notification = NotificationEvent(
                    timestamp=datetime.now(),
                    title="Active Session Found",
                    content=f"There is an active session for player: {active_session.player_name or 'Unknown'}",
                    severity=NotificationSeverity.WARNING,
                    duration=8000  # Show for 8 seconds
                )
                await self.publish(notification)
                logger.info(f"📋 Sent notification about active session for player: {active_session.player_name}")
