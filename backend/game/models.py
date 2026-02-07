# game/models.py - UPDATED
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
    room_id: str = ""
    photon_room: str = ""
    players: List[str] = []
    usernames: Dict[str, str] = {}
    error: str = ""