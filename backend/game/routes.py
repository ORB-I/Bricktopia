# game/routes.py - UPDATED VERSION
from fastapi import APIRouter, HTTPException
import uuid
import time
from typing import Dict
from .models import CreateRoomRequest, JoinRoomRequest, GameActionRequest, RoomResponse

router = APIRouter()

# Import shared state and cleanup
from .cleanup import rooms, player_sessions, start_cleanup_task

# Start cleanup on startup
@router.on_event("startup")
async def startup_event():
    await start_cleanup_task()

@router.post("/create-room", response_model=RoomResponse)
async def create_room(request: CreateRoomRequest):
    """Create a new game room"""
    room_id = str(uuid.uuid4())[:6].lower()
    rooms[room_id] = {
        "id": room_id,
        "host": request.player_id,
        "players": [request.player_id],
        "created_at": time.time(),
        "state": {
            "scores": {},
            "started": False,
            "turn": 0,
            "last_activity": time.time()
        }
    }
    player_sessions[request.player_id] = room_id
    
    return RoomResponse(
        success=True,
        room_id=room_id,
        photon_room=f"brick_{room_id}",
        players=[request.player_id]
    )

@router.post("/join-room", response_model=RoomResponse)
async def join_room(request: JoinRoomRequest):
    """Join existing room"""
    if request.room_id not in rooms:
        return RoomResponse(success=False, error="Room not found")
    
    room = rooms[request.room_id]
    
    # Update last activity
    room["state"]["last_activity"] = time.time()
    
    if request.player_id in room["players"]:
        return RoomResponse(
            success=True,
            room_id=request.room_id,
            photon_room=f"brick_{request.room_id}",
            players=room["players"]
        )
    
    if len(room["players"]) >= 8:
        return RoomResponse(success=False, error="Room full (max 8 players)")
    
    room["players"].append(request.player_id)
    player_sessions[request.player_id] = request.room_id
    
    return RoomResponse(
        success=True,
        room_id=request.room_id,
        photon_room=f"brick_{request.room_id}",
        players=room["players"]
    )

@router.post("/game-action")
async def game_action(request: GameActionRequest):
    """Process game action (move, shoot, etc.)"""
    room_id = player_sessions.get(request.player_id)
    if not room_id or room_id not in rooms:
        raise HTTPException(status_code=400, detail="Not in a valid room")
    
    room = rooms[room_id]
    room["state"]["last_activity"] = time.time()
    
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

@router.get("/room/{room_id}")
async def get_room(room_id: str):
    """Get room info (for reconnection)"""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Update last activity on polling
    rooms[room_id]["state"]["last_activity"] = time.time()
    
    return rooms[room_id]

@router.post("/leave-room")
async def leave_room(request: JoinRoomRequest):
    """Leave current room"""
    room_id = player_sessions.pop(request.player_id, None)
    
    if room_id and room_id in rooms:
        room = rooms[room_id]
        if request.player_id in room["players"]:
            room["players"].remove(request.player_id)
            
            # If room is empty, delete it
            if len(room["players"]) == 0:
                del rooms[room_id]
                print(f"Deleted empty room: {room_id}")
            # If host left, assign new host
            elif request.player_id == room["host"] and room["players"]:
                room["host"] = room["players"][0]
    
    return {"success": True}

@router.get("/health")
async def health():
    """Game service health check"""
    return {
        "status": "healthy",
        "service": "game",
        "active_rooms": len(rooms),
        "active_players": len(player_sessions)
    }