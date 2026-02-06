# game/routes.py - COMPLETE FIXED VERSION
from fastapi import APIRouter, HTTPException
import uuid
import time
from typing import Dict
from .models import CreateRoomRequest, JoinRoomRequest, GameActionRequest, RoomResponse

router = APIRouter()

# In-memory game state
rooms: Dict[str, Dict] = {}
player_sessions: Dict[str, str] = {}  # player_id → room_id

@router.post("/create-room", response_model=RoomResponse)
async def create_room(request: CreateRoomRequest):
    """Create a new game room"""
    try:
        print(f"🎮 Creating room for player: {request.player_id}")
        
        room_id = str(uuid.uuid4())[:6].lower()
        
        rooms[room_id] = {
            "id": room_id,
            "host": request.player_id,
            "players": [request.player_id],
            "created_at": time.time(),
            "state": {
                "scores": {},
                "started": False,
                "turn": 0
            }
        }
        player_sessions[request.player_id] = room_id
        
        print(f"✅ Room created: {room_id}")
        
        return RoomResponse(
            success=True,
            room_id=room_id,
            photon_room=f"brick_{room_id}",
            players=[request.player_id]
        )
        
    except Exception as e:
        print(f"❌ Error creating room: {e}")
        import traceback
        traceback.print_exc()
        return RoomResponse(
            success=False,
            error=f"Server error: {str(e)}"
        )

@router.post("/join-room", response_model=RoomResponse)
async def join_room(request: JoinRoomRequest):
    """Join existing room"""
    try:
        print(f"🎮 Player {request.player_id} joining room {request.room_id}")
        
        if request.room_id not in rooms:
            return RoomResponse(success=False, error="Room not found")
        
        room = rooms[request.room_id]
        
        # Check if player already in room
        if request.player_id in room["players"]:
            return RoomResponse(
                success=True,
                room_id=request.room_id,
                photon_room=f"brick_{request.room_id}",
                players=room["players"]
            )
        
        # Check room capacity
        if len(room["players"]) >= 8:
            return RoomResponse(success=False, error="Room full (max 8 players)")
        
        # Add player to room
        room["players"].append(request.player_id)
        player_sessions[request.player_id] = request.room_id
        
        print(f"✅ Player joined. Room now has: {room['players']}")
        
        return RoomResponse(
            success=True,
            room_id=request.room_id,
            photon_room=f"brick_{request.room_id}",
            players=room["players"]
        )
        
    except Exception as e:
        print(f"❌ Error joining room: {e}")
        return RoomResponse(
            success=False,
            error=f"Server error: {str(e)}"
        )

@router.get("/room/{room_id}")
async def get_room(room_id: str):
    """Get room info"""
    try:
        if room_id not in rooms:
            raise HTTPException(status_code=404, detail="Room not found")
        return rooms[room_id]
    except Exception as e:
        print(f"❌ Error getting room: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/game-action")
async def game_action(request: GameActionRequest):
    """Process game action"""
    try:
        room_id = player_sessions.get(request.player_id)
        if not room_id or room_id not in rooms:
            raise HTTPException(status_code=400, detail="Not in a valid room")
        
        room = rooms[room_id]
        
        if request.action == "start_game":
            room["state"]["started"] = True
            room["state"]["start_time"] = time.time()
        
        room["state"]["last_action"] = {
            "player": request.player_id,
            "action": request.action,
            "data": request.data,
            "timestamp": time.time()
        }
        
        return {
            "success": True,
            "room_state": room["state"],
            "room_id": room_id
        }
        
    except Exception as e:
        print(f"❌ Game action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    """Game service health check"""
    return {
        "status": "healthy",
        "service": "game",
        "active_rooms": len(rooms),
        "active_players": len(player_sessions)
    }