# Oracle/services/ws_broadcast.py

import asyncio
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Any

from fastapi import WebSocket

from Oracle.parsing.parsers.events import ParserEvent
from Oracle.parsing.parsers.events.parser_event_type import ParserEventType
from Oracle.parsing.parsers.events.player_join import PlayerJoinEvent
from Oracle.parsing.parsers.events.stage_affix import StageAffixEvent

from Oracle.events import EventBus
from Oracle.services.events.map_events import MapStartedEvent, MapStatusEvent, MapFinishedEvent, MapRecordEvent
from Oracle.services.events.market_events import MarketActionEvent, MarketTransactionEvent
from Oracle.services.events.notification_events import NotificationEvent
from Oracle.services.events.service_event import ServiceEventType, ServiceEvent
from Oracle.services.events.session_events import SessionStartedEvent, SessionFinishedEvent, SessionRestoreEvent
from Oracle.services.events.stats_events import StatsUpdateEvent
from Oracle.services.events.level_events import LevelProgressEvent
from Oracle.services.events.item_events import ItemObtainedEvent, ItemDataChangedEvent
from Oracle.services.events.hotkey_events import HotkeyPressedEvent
from Oracle.services.events.overlay_events import OverlayBoundsUpdateEvent, HoverEnterEvent, HoverLeaveEvent, OverlayInfoTextEvent, ViewChangedEvent
from Oracle.services.events.websocket_events import WebSocketEvent, WebSocketStatus
from Oracle.services.service_base import ServiceBase

from Oracle.services.tooling.decorators import event_handler

from Oracle.tooling.logger import Logger

logger = Logger("WebSocketBroadcastService")

class WebSocketBroadcastService(ServiceBase):
    """
    Broadcasts events to connected WebSocket clients.
    """
    
    __SERVICE__ = {
        "name": "WebSocketService",
        "version": "1.0.0",
        "description": "Broadcasts parser and service events to connected WebSocket clients",
        "requires": {}
    }
    
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.clients: List[WebSocket] = []
        self._heartbeat_task: asyncio.Task | None = None
        self._server_version = self._load_version()
        logger.info("🕸️  WebSocketBroadcastService initialized")

    def _load_version(self) -> str:
        try:
            # Production: build.json next to server root
            build_path = Path(__file__).parent.parent.parent / "build.json"
            if not build_path.exists():
                # Development: deploy/targets/server/build.json
                build_path = Path(__file__).parent.parent.parent.parent / "deploy" / "targets" / "server" / "build.json"
            with open(build_path) as f:
                return json.load(f).get("version", "unknown")
        except Exception:
            return "dev"

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(1)
            if self.clients:
                await self._broadcast_to_clients({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat(),
                    "name": "server",
                    "version": self._server_version
                })

    def _serialize_value(self, value: Any) -> Any:
        """Recursively serialize a single value to JSON-compatible format."""
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, dict):
            # Convert tuple keys to strings for JSON compatibility
            return {
                (str(k) if isinstance(k, tuple) else k): self._serialize_value(v)
                for k, v in value.items()
            }
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in value]
        elif hasattr(value, 'slots') and hasattr(value, 'copy'):
            # Handle Inventory objects - serialize slots with string keys
            return {
                f"{page},{slot}": self._serialize_value(item)
                for (page, slot), item in value.slots.items()
            }
        elif hasattr(value, '__dict__'):
            # Handle dataclasses and custom objects
            return self._serialize_value(value.__dict__)
        else:
            # Fallback to string representation
            return str(value)

    def _serialize_data(self, data: dict) -> dict:
        """Convert all objects to JSON-serializable format."""
        return {key: self._serialize_value(value) for key, value in data.items()}

    async def _broadcast_to_clients(self, data: dict):
        """Broadcast data to all connected WebSocket clients."""
        #ogger.debug(f"🕸️ Broadcasting to {len(self.clients)} client(s), event type: {data.get('type', 'unknown')}")
        
        # Serialize datetime objects before sending
        try:
            serialized_data = self._serialize_data(data)
        except Exception as e:
            logger.error(f"🕸️ Failed to serialize data: {e}")
            logger.debug(f"Data: {data}")
            return
        
        dead = []
        for ws in self.clients:
            try:
                await ws.send_json(serialized_data)
                #ogger.debug(f"🕸️ ✅ Sent {serialized_data.get('type')} to {ws.client}")
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                # Network errors - client is dead
                logger.warning(f"🕸️ Connection lost to {ws.client}: {e}")
                dead.append(ws)
            except Exception as e:
                # Other errors - log but don't kill the client
                logger.error(f"🕸️ Error sending to {ws.client}: {e}")
                logger.trace(e)

        for d in dead:
            self.clients.remove(d)
            logger.info(f"🕸️ Removed dead client: {d.client}")

    @event_handler(ServiceEventType.WEBSOCKET_CONNECTED)
    async def on_websocket_connected(self, event: WebSocketEvent):
        """Handle WebSocket connection."""
        self.clients.append(event.websocket)
        logger.info(f"🕸️ Client connected: {event.client_info} - Total clients: {len(self.clients)}")
        # Publish CLIENT_CONNECTED event so other services can send their current state
        logger.debug(f"🕸️ Publishing CLIENT_CONNECTED event for other services")
        await self.publish(ServiceEvent(timestamp=datetime.now(), type=ServiceEventType.CLIENT_CONNECTED))

    @event_handler(ServiceEventType.WEBSOCKET_DISCONNECTED)
    async def on_websocket_disconnected(self, event: WebSocketEvent):
        """Handle WebSocket disconnection."""
        if event.websocket in self.clients:
            self.clients.remove(event.websocket)
        logger.info(f"🕸️ Client disconnected: {event.client_info} - Total clients: {len(self.clients)}")

    @event_handler(ServiceEventType.MAP_STARTED)
    async def on_map_started(self, event: MapStartedEvent):
        """Broadcast map started event to clients."""
        logger.debug(f"🕸️ Broadcasting MapStartedEvent: {event.level_id}")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.MAP_STATUS)
    async def on_map_status(self, event: MapStatusEvent):
        """Broadcast current map status to clients (sent on client connect, does not trigger stats)."""
        logger.debug(f"🕸️ Broadcasting MapStatusEvent: {event.level_id}")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.MAP_FINISHED)
    async def on_map_finished(self, event: MapFinishedEvent):
        """Broadcast map finished event to clients."""
        logger.debug(f"🕸️ Broadcasting MapFinishedEvent - Duration: {event.duration:.2f}s")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.STATS_UPDATE)
    async def on_stats_update(self, event: StatsUpdateEvent):
        """Broadcast stats update event to clients."""
        logger.debug(f"🕸️ Broadcasting StatsUpdateEvent - {event.total_maps} maps")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ParserEventType.PLAYER_JOIN)
    async def on_player_join(self, event: PlayerJoinEvent):
        """Broadcast player join event to clients."""
        logger.debug(f"🕸️ Broadcasting PlayerJoinEvent: {event.player_name}")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ParserEventType.STAGE_AFFIX)
    async def on_stage_affix(self, event: StageAffixEvent):
        """Broadcast stage affix event to clients."""
        logger.debug(f"🕸️ Broadcasting StageAffixEvent: {len(event.affixes)} affixes")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.SESSION_STARTED)
    async def on_session_started(self, event: SessionStartedEvent):
        """Broadcast session started event to clients."""
        logger.debug(f"🕸️  Broadcasting SessionStartedEvent: session_id={event.session_id}, player={event.player_name}")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.SESSION_FINISHED)
    async def on_session_finished(self, event: SessionFinishedEvent):
        """Broadcast session finished event to clients."""
        logger.debug(f"🕸️  Broadcasting SessionFinishedEvent: session_id={event.session_id}, player={event.player_name}")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.SESSION_RESTORE)
    async def on_session_restore(self, event: SessionRestoreEvent):
        """Broadcast session restore event to clients."""
        logger.debug(f"🕸️  ⚡ Broadcasting SessionRestoreEvent: player={event.player_name}, maps={event.total_maps}")
        await self._broadcast_to_clients(event.to_dict())
        logger.debug(f"🕸️  ⚡ SessionRestoreEvent broadcast complete")

    @event_handler(ServiceEventType.MAP_RECORD)
    async def on_map_record(self, event: MapRecordEvent):
        """Broadcast map record event to clients."""
        map_id = event.map_record.get('id', 'unknown')
        logger.debug(f"🕸️  Broadcasting MapRecordEvent: map_id={map_id}")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.NOTIFICATION)
    async def on_notification(self, event: NotificationEvent):
        """Broadcast notification event to clients."""
        logger.debug(f"🕸️ Broadcasting NotificationEvent: {event.title} ({event.severity.value})")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.ITEM_OBTAINED)
    async def on_item_obtained(self, event: ItemObtainedEvent):
        """Broadcast item obtained event to clients."""
        action = "gained" if event.delta > 0 else "lost"
        logger.debug(f"🕸️ Broadcasting ItemObtainedEvent: {event.item_name or event.item_id} {action} {abs(event.delta)}")
        await self._broadcast_to_clients(event.to_dict())
    
    @event_handler(ServiceEventType.ITEM_DATA_CHANGED)
    async def on_item_data_changed(self, event: ItemDataChangedEvent):
        """Broadcast item data changed event to clients."""
        logger.debug(f"🕸️ Broadcasting ItemDataChangedEvent: {event.name or event.item_id} price={event.price}")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.MARKET_ACTION)
    async def on_market_close(self, event: MarketActionEvent):
        """Broadcast market close event to clients."""
        logger.debug(f"🕸️ Broadcasting MarketActionEvent: {event.action.value}")
        await self._broadcast_to_clients(event.to_dict())
    
    @event_handler(ServiceEventType.MARKET_TRANSACTION)
    async def on_market_transaction(self, event: MarketTransactionEvent):
        """Broadcast market transaction event to clients."""
        logger.debug(f"🕸️ Broadcasting MarketTransactionEvent: {event.action} {event.quantity}x item {event.item_id}")
        await self._broadcast_to_clients(event.to_dict())
    
    @event_handler(ServiceEventType.LEVEL_PROGRESS)
    async def on_level_progress(self, event: LevelProgressEvent):
        """Broadcast level progress event to clients."""
        logger.debug(f"🕸️ Broadcasting LevelProgressEvent: Level {event.level} - {event.percentage:.1f}%")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.HOTKEY_PRESSED)
    async def on_hotkey_pressed(self, event: HotkeyPressedEvent):
        """Broadcast hotkey pressed event to clients."""
        logger.debug(f"🕸️ Broadcasting HotkeyPressedEvent: key={event.key}")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.OVERLAY_BOUNDS_UPDATE)
    async def on_overlay_bounds_update(self, event: OverlayBoundsUpdateEvent):
        """Broadcast overlay bounds update to clients (consumed by Oracle-Hotkey)."""
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.HOVER_ENTER)
    async def on_hover_enter(self, event: HoverEnterEvent):
        """Broadcast hover enter event to clients."""
        logger.debug("🕸️ Broadcasting HoverEnterEvent")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.HOVER_LEAVE)
    async def on_hover_leave(self, event: HoverLeaveEvent):
        """Broadcast hover leave event to clients."""
        logger.debug("🕸️ Broadcasting HoverLeaveEvent")
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.OVERLAY_INFO_TEXT)
    async def on_overlay_info_text(self, event: OverlayInfoTextEvent):
        """Broadcast overlay info text to clients."""
        await self._broadcast_to_clients(event.to_dict())

    @event_handler(ServiceEventType.VIEW_CHANGED)
    async def on_view_changed(self, event: ViewChangedEvent):
        """Broadcast view changed event to clients."""
        await self._broadcast_to_clients(event.to_dict())

    async def handle_event(self, event: ParserEvent):
        pass 

    async def startup(self):
        """Initialize websocket service."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"🕸️ Heartbeat started (server v{self._server_version})")

    async def shutdown(self):
        """Shutdown websocket service and close all connections."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        logger.info(f"🕸️ Shutting down WebSocketBroadcastService ({len(self.clients)} clients)")
        
        # Close all WebSocket connections gracefully
        for ws in self.clients:
            try:
                await ws.close(code=1000, reason="Server shutting down")
                logger.debug(f"🕸️ Closed connection to {ws.client}")
            except Exception as e:
                logger.warning(f"🕸️ Error closing connection to {ws.client}: {e}")
        
        # Clear the clients list
        self.clients.clear()
        logger.info("🕸️ WebSocketBroadcastService shutdown complete")

