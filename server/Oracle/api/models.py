"""Pydantic response models for API endpoints."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Map models
class MapCompletionResponse(BaseModel):
    """Response model for a single map completion."""
    id: int
    player_name: Optional[str]
    map_id: Optional[str]
    map_name: str
    map_difficulty: Optional[str]
    started_at: str
    completed_at: str
    duration: Optional[float]
    currency_gained: Optional[float]
    exp_gained: Optional[float]
    items_gained: Optional[int]
    description: Optional[str]


class MapsPaginatedResponse(BaseModel):
    """Paginated response for maps endpoint."""
    total: int = Field(..., description="Total number of maps matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    results: List[MapCompletionResponse]


class MapUpdateRequest(BaseModel):
    """Request model for updating map completion."""
    description: Optional[str] = Field(None, description="Description or notes for the map run")


class MapUpdateResponse(BaseModel):
    """Response after updating a map."""
    id: int
    description: Optional[str]
    message: str


# Session models
class SessionMapSummary(BaseModel):
    """Summary of a map in a session."""
    id: int
    map_name: str
    map_difficulty: Optional[str]
    completed_at: str
    duration: Optional[float]
    currency_gained: Optional[float]
    exp_gained: Optional[float]


class SessionResponse(BaseModel):
    """Response model for a farming session."""
    id: int
    player_name: str
    started_at: str
    ended_at: Optional[str]
    total_maps: int
    total_currency_delta: Optional[float]
    currency_per_hour: Optional[float]
    currency_per_map: Optional[float]
    description: Optional[str]


class ActiveSessionResponse(BaseModel):
    """Response for active session endpoint."""
    session: Optional[Dict[str, Any]]


class SessionsPaginatedResponse(BaseModel):
    """Paginated response for sessions endpoint."""
    total: int
    page: int
    page_size: int
    total_pages: int
    results: List[SessionResponse]


class SessionUpdateRequest(BaseModel):
    """Request to update session description."""
    description: str = Field(..., description="New description for the session")


# Inventory models
class InventorySlot(BaseModel):
    """Single inventory slot."""
    slot: int
    item_name: str
    item_id: Optional[str]
    quantity: int
    timestamp: str


class InventoryResponse(BaseModel):
    """Response for inventory endpoint."""
    inventory: Dict[str, Dict[int, List[InventorySlot]]]


# Status models
class StatusResponse(BaseModel):
    """Response for status endpoint."""
    status: str
    log_reader_status: str
    loaded_parsers: List[str]
    loaded_services: List[str]


class RootResponse(BaseModel):
    """Response for root endpoint."""
    status: str
    message: str


# Stats models
class StatsResetResponse(BaseModel):
    """Response after resetting stats."""
    status: str
    message: str


# Error models
class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
