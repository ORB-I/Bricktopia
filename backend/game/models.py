# game/models.py
from pydantic import BaseModel
from typing import List, Dict, Optional

class CreateRoomRequest(BaseModel):
    player_id: str

class JoinRoomRequest(BaseModel):
    room_id: str
    player_id: str

class GameActionRequest(BaseModel):
    player_id: str
    action: str
    data: Dict = {}

class RoomResponse(BaseModel):
    success: bool
    room_id: Optional[str] = None
    photon_room: Optional[str] = None
    players: List[str] = []
    usernames: Dict[str, str] = {}  # This line is CRITICAL!
    error: str = ""