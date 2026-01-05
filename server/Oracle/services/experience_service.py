import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from Oracle.database.models import Player
from Oracle.parsing.parsers.events import ParserEventType
from Oracle.parsing.parsers.events.exp_update import ExpUpdateEvent
from Oracle.parsing.parsers.events.player_join import PlayerJoinEvent
from Oracle.events import EventBus
from Oracle.services.events.level_events import LevelProgressEvent
from Oracle.services.events.session_events import PlayerChangedEvent
from Oracle.services.events.service_event import ServiceEventType
from Oracle.services.service_base import ServiceBase
from Oracle.services.tooling.decorators import event_handler
from Oracle.tooling.logger import Logger
from Oracle.tooling.paths import REPO_ROOT

logger = Logger("ExperienceService")


class ExperienceService(ServiceBase):
    """Service that tracks character level and experience progress."""
    
    __SERVICE__ = {
        "name": "ExperienceService",
        "version": "0.0.1",
        "description": "Tracks character level and experience progress",
        "requires": {}
    }

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        
        # Load experience table
        self.exp_table: Dict[int, int] = {}
        self._load_experience_table()
        
        # Current state
        self.current_level: int = 1
        self.current_exp: int = 0
        self.total_exp_gained: int = 0  # Total exp gained in session
        
        logger.info("🎓 ExperienceService initialized")

    def _load_experience_table(self):
        """Load experience requirements from Experience.json."""
        try:
            exp_file = REPO_ROOT / "Experience.json"
            if not exp_file.exists():
                logger.error(f"Experience.json not found at {exp_file}")
                return
                
            with open(exp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Parse the experience table
            # Format: {"levels": [[{"Id": 1, "Exp": 4346, ...}, ...]], ...}
            levels_data = data.get("levels", [[]])[0]
            
            for level_info in levels_data:
                level_id = level_info["Id"]
                exp_required = level_info["Exp"]
                self.exp_table[level_id] = exp_required
            
            logger.info(f"📊 Loaded experience table with {len(self.exp_table)} levels")
            
        except Exception as e:
            logger.error(f"Failed to load experience table: {e}", exc_info=True)

    def _calculate_level_progress(self, level: int, experience: int) -> Optional[LevelProgressEvent]:
        """Calculate level progress based on current exp."""
        if level not in self.exp_table:
            logger.warning(f"Level {level} not found in experience table")
            return None
        
        level_total = self.exp_table[level]
        current = experience
        remaining = max(0, level_total - current)
        percentage = (current / level_total * 100.0) if level_total > 0 else 0.0
        
        return LevelProgressEvent(
            timestamp=datetime.now(),
            level=level,
            current=current,
            remaining=remaining,
            level_total=level_total,
            percentage=percentage
        )

    @event_handler(ParserEventType.EXP_UPDATE)
    async def on_exp_update(self, event: ExpUpdateEvent):
        """Handle experience update from parser."""
        logger.debug(f"🎓 Exp update: Level {event.level}, Exp {event.experience}")
        
        # Update state
        prev_level = self.current_level
        self.current_level = event.level
        self.current_exp = event.experience
        
        # Check for level up
        if prev_level != event.level and prev_level > 0:
            logger.info(f"🎉 Level up! {prev_level} -> {event.level}")
        
        # Calculate and emit level progress
        progress_event = self._calculate_level_progress(event.level, event.experience)
        if progress_event:
            await self.publish(progress_event)
            logger.debug(
                f"📊 Level {progress_event.level}: "
                f"{progress_event.current}/{progress_event.level_total} "
                f"({progress_event.percentage:.1f}%) "
                f"- {progress_event.remaining} remaining"
            )

            player = await self.get_player()
            if not player:
                return
            # Update player level and experience
            player.level = progress_event.level
            player.experience = progress_event.current
            await player.save()
    
            logger.debug(f"💾 Updated player {player.name}: Level {progress_event.level}, Exp {progress_event.current}/{progress_event.level_total} ({progress_event.percentage:.1f}%)")
            
    @event_handler(ParserEventType.PLAYER_JOIN)
    async def on_player_join(self, event: PlayerJoinEvent):
        """Load player level/experience from database and publish initial level progress."""
        if not event.player_name:
            return
        
        # Get or create player
        player, created = await Player.get_or_create(
            name=event.player_name,
            defaults={"level": 1, "experience": 0}
        )
        
        # Update current state
        self.current_level = player.level
        self.current_exp = player.experience
        
        # Publish initial level progress event
        progress_event = self._calculate_level_progress(player.level, player.experience)
        if progress_event:
            await self.publish(progress_event)
            logger.info(
                f"🎓 Loaded player {player.name}: Level {player.level}, "
                f"Exp {player.experience}/{self.exp_table.get(player.level, 0)} "
                f"({progress_event.percentage:.1f}%)"
            )

    async def startup(self):
        """Initialize service resources."""
        pass

    async def shutdown(self):
        """Cleanup service resources."""
        pass
