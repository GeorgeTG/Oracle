"""
Database models using Tortoise ORM.
"""
from enum import Enum
from tortoise import fields
from tortoise.models import Model


class PriceSource(str, Enum):
    """Enum for price data sources."""
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


class Player(Model):
    """Player information."""
    
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    level = fields.IntField(default=1)
    experience = fields.IntField(default=0)
    last_seen = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "players"

class Item(Model):
    """Game items."""
    
    id = fields.IntField(pk=True)
    item_id = fields.IntField(unique=True)  # Game's internal item ID
    name = fields.CharField(max_length=255, null=True)
    category = fields.CharField(max_length=100, null=True)
    rarity = fields.CharField(max_length=50, null=True)
    price = fields.FloatField(default=0.0)  # Item price
    updated_at = fields.DatetimeField(auto_now=True)  # Last update timestamp
    
    class Meta:
        table = "items"


class InventoryItem(Model):
    """Player inventory items with page and slot information."""
    
    id = fields.IntField(pk=True)
    player = fields.ForeignKeyField("models.Player", related_name="inventory_items")
    item = fields.ForeignKeyField("models.Item", related_name="in_inventories")
    page = fields.IntField()
    slot = fields.IntField()
    quantity = fields.IntField(default=1)
    timestamp = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "inventory_items"


class Inventory(Model):
    """Player inventory snapshots (deprecated - use InventoryItem)."""
    
    id = fields.IntField(pk=True)
    player = fields.ForeignKeyField("models.Player", related_name="inventory_legacy")
    item = fields.ForeignKeyField("models.Item", related_name="inventory_legacy_entries")
    quantity = fields.IntField(default=1)
    timestamp = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "inventory"


class ExpSnapshot(Model):
    """Experience/level snapshots over time."""
    
    id = fields.IntField(pk=True)
    player = fields.ForeignKeyField("models.Player", related_name="exp_snapshots", null=True)
    timestamp = fields.DatetimeField()
    level = fields.IntField()
    exp_percent = fields.IntField()
    
    class Meta:
        table = "exp_snapshots"


class Session(Model):
    """Farming session statistics."""
    
    id = fields.IntField(pk=True)
    player = fields.ForeignKeyField("models.Player", related_name="farming_sessions", null=True)
    player_name = fields.CharField(max_length=255, null=True)
    
    # Session status
    is_active = fields.BooleanField(default=False)
    
    # Session timing
    started_at = fields.DatetimeField(auto_now_add=True)
    ended_at = fields.DatetimeField(null=True)
    
    # Session statistics
    total_maps = fields.IntField(default=0)
    total_currency_delta = fields.FloatField(default=0.0)
    currency_per_hour = fields.FloatField(default=0.0)
    currency_per_map = fields.FloatField(default=0.0)
    
    # Stats service state (for restore)
    total_time = fields.FloatField(default=0.0)  # Total farming time in seconds
    exp_total = fields.FloatField(default=0.0)  # Total exp gained
    exp_per_hour = fields.FloatField(default=0.0)  # Exp per hour rate
    currency_total = fields.FloatField(default=0.0)  # Total currency gained
    
    # Optional title and description
    title = fields.CharField(max_length=255, null=True)
    description = fields.TextField(null=True)
    
    class Meta:
        table = "sessions"


class MapVisit(Model):
    """Track map visits and transitions."""
    
    id = fields.IntField(pk=True)
    player = fields.ForeignKeyField("models.Player", related_name="map_visits", null=True)
    timestamp = fields.DatetimeField()
    map_path = fields.TextField()
    map_name = fields.CharField(max_length=255, null=True)
    
    class Meta:
        table = "map_visits"


class MapCompletion(Model):
    """Track completed maps with statistics."""
    
    id = fields.IntField(pk=True)
    player = fields.ForeignKeyField("models.Player", related_name="map_completions")
    session = fields.ForeignKeyField("models.Session", related_name="map_completions", null=True)
    
    # Map information
    map_id = fields.IntField()
    map_name = fields.CharField(max_length=255, null=True)
    map_difficulty = fields.CharField(max_length=50, null=True)
    
    # Timing
    started_at = fields.DatetimeField()
    completed_at = fields.DatetimeField()
    duration = fields.FloatField()  # seconds
    
    # Statistics
    currency_gained = fields.FloatField(default=0.0)
    exp_gained = fields.FloatField(default=0.0)
    items_gained = fields.IntField(default=0)  # Number of new items
    
    # Optional description
    description = fields.TextField(null=True)
    
    class Meta:
        table = "map_completions"


class MapCompletionItem(Model):
    """Track individual items gained/lost in a map completion."""
    
    id = fields.IntField(pk=True)
    map_completion = fields.ForeignKeyField("models.MapCompletion", related_name="items")
    item = fields.ForeignKeyField("models.Item", related_name="map_drops")
    delta = fields.IntField()  # Positive for gains, negative for losses
    total_price = fields.FloatField(default=0.0)  # Total value for this delta
    consumed = fields.BooleanField(default=False)  # True if item was consumed before entering map
    
    class Meta:
        table = "map_completion_items"


class Affix(Model):
    """Track unique map affixes."""
    
    id = fields.IntField(pk=True)
    affix_id = fields.IntField(unique=True)  # Game's affix ID
    description = fields.CharField(max_length=500, null=True)
    
    class Meta:
        table = "affixes"


class MapAffix(Model):
    """Many-to-many relation between map completions and affixes."""
    
    id = fields.IntField(pk=True)
    map_completion = fields.ForeignKeyField("models.MapCompletion", related_name="affixes")
    affix = fields.ForeignKeyField("models.Affix", related_name="map_completions")
    
    class Meta:
        table = "map_affixes"
        unique_together = (("map_completion", "affix"),)  # Prevent duplicate affixes per map


class MarketTransaction(Model):
    """Track market (auction house) transactions."""
    
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.Session", related_name="market_transactions", null=True)
    player = fields.ForeignKeyField("models.Player", related_name="market_transactions", null=True)
    
    # Transaction details
    timestamp = fields.DatetimeField()
    item = fields.ForeignKeyField("models.Item", related_name="market_transactions")
    quantity = fields.IntField()
    action = fields.CharField(max_length=10)  # "bought" or "sold"
    
    class Meta:
        table = "market_transactions"


class PriceDataBaseRevision(Model):
    """Track price database revisions and their sources."""
    
    id = fields.IntField(pk=True)
    timestamp = fields.DatetimeField(auto_now_add=True)
    source = fields.CharEnumField(enum_type=PriceSource, max_length=10)
    item_count = fields.IntField(default=0)
    
    class Meta:
        table = "price_db_revisions"

