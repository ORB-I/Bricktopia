# backend/game/models.py
from pydantic import BaseModel
from typing import List, Dict, Optional

class CreateRoomRequest(BaseModel):
    # player_id removed - comes from auth token
    public: bool = True  # Whether room appears in server browser

class JoinRoomRequest(BaseModel):
    room_id: str
    # player_id removed - comes from auth token

class GameActionRequest(BaseModel):
    # player_id removed - comes from auth token
    action: str
    data: Dict = {}

class RoomResponse(BaseModel):
    success: bool
    room_id: str = None
    photon_room: str = None
    players: List[str] = []
    error: str = ""