# backend/game/routes.py
from fastapi import APIRouter, HTTPException, Depends
import uuid
import time
from typing import Dict
from .models import CreateRoomRequest, JoinRoomRequest, GameActionRequest, RoomResponse
from auth.middleware import get_current_user

router = APIRouter()

# In-memory game state
rooms: Dict[str, Dict] = {}
player_sessions: Dict[str, str] = {}  # player_id → room_id

@router.post("/create-room", response_model=RoomResponse)
async def create_room(
    request: CreateRoomRequest,
    current_user: dict = Depends(get_current_user)  # ← REQUIRES AUTH
):
    """Create a new game room (requires authentication)"""
    # Use verified user_id from token, not from request body
    player_id = current_user["user_id"]
    
    room_id = str(uuid.uuid4())[:6].lower()
    rooms[room_id] = {
        "id": room_id,
        "host": player_id,
        "players": [player_id],
        "created_at": time.time(),
        "public": request.public if hasattr(request, 'public') else True,
        "state": {
            "scores": {},
            "started": False,
            "turn": 0
        }
    }
    player_sessions[player_id] = room_id
    
    return RoomResponse(
        success=True,
        room_id=room_id,
        photon_room=f"brick_{room_id}",
        players=[player_id]
    )

@router.post("/join-room", response_model=RoomResponse)
async def join_room(
    request: JoinRoomRequest,
    current_user: dict = Depends(get_current_user)  # ← REQUIRES AUTH
):
    """Join existing room (requires authentication)"""
    # Use verified user_id from token
    player_id = current_user["user_id"]
    
    if request.room_id not in rooms:
        return RoomResponse(success=False, error="Room not found")
    
    room = rooms[request.room_id]
    
    # Check if player already in room
    if player_id in room["players"]:
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
    room["players"].append(player_id)
    player_sessions[player_id] = request.room_id
    
    return RoomResponse(
        success=True,
        room_id=request.room_id,
        photon_room=f"brick_{request.room_id}",
        players=room["players"]
    )

@router.post("/game-action")
async def game_action(
    request: GameActionRequest,
    current_user: dict = Depends(get_current_user)  # ← REQUIRES AUTH
):
    """Process game action (requires authentication)"""
    # Use verified user_id from token
    player_id = current_user["user_id"]
    
    room_id = player_sessions.get(player_id)
    if not room_id or room_id not in rooms:
        raise HTTPException(status_code=400, detail="Not in a valid room")
    
    room = rooms[room_id]
    
    # Verify player is in the room
    if player_id not in room["players"]:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    # Update game state based on action
    if request.action == "start_game":
        # Only host can start game
        if player_id != room["host"]:
            raise HTTPException(status_code=403, detail="Only host can start game")
        
        room["state"]["started"] = True
        room["state"]["start_time"] = time.time()
    
    # Store last action
    room["state"]["last_action"] = {
        "player": player_id,
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
async def get_room(
    room_id: str,
    current_user: dict = Depends(get_current_user)  # ← REQUIRES AUTH
):
    """Get room info (requires authentication)"""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    player_id = current_user["user_id"]
    
    # Can only view rooms you're in or public rooms
    if player_id not in room["players"] and not room.get("public", True):
        raise HTTPException(status_code=403, detail="Cannot view private room")
    
    return room

@router.get("/rooms/list")
async def list_rooms():
    """Get all public rooms (no auth required for browsing)"""
    public_rooms = []
    for room_id, room_data in rooms.items():
        if room_data.get("public", True) and not room_data["state"].get("started", False):
            public_rooms.append({
                "room_id": room_id,
                "player_count": len(room_data["players"]),
                "max_players": 8,
                "created_at": room_data["created_at"]
            })
    return {"success": True, "rooms": public_rooms}

@router.post("/rooms/quick-join")
async def quick_join(
    current_user: dict = Depends(get_current_user)  # ← REQUIRES AUTH
):
    """Join first available room or create new one (requires authentication)"""
    player_id = current_user["user_id"]
    
    # Find available room
    available = [r for r in rooms.values() 
                 if len(r["players"]) < 8 
                 and r.get("public", True)
                 and not r["state"].get("started", False)]
    
    if available:
        # Join least full room
        room = min(available, key=lambda r: len(r["players"]))
        
        # Add player
        if player_id not in room["players"]:
            room["players"].append(player_id)
            player_sessions[player_id] = room["id"]
        
        return RoomResponse(
            success=True,
            room_id=room["id"],
            photon_room=f"brick_{room['id']}",
            players=room["players"]
        )
    else:
        # Create new room
        return await create_room(
            CreateRoomRequest(player_id=player_id),
            current_user=current_user
        )

@router.post("/leave-room")
async def leave_room(
    current_user: dict = Depends(get_current_user)  # ← REQUIRES AUTH
):
    """Leave current room (requires authentication)"""
    player_id = current_user["user_id"]
    
    room_id = player_sessions.get(player_id)
    if not room_id or room_id not in rooms:
        return {"success": False, "error": "Not in a room"}
    
    room = rooms[room_id]
    
    # Remove player from room
    if player_id in room["players"]:
        room["players"].remove(player_id)
    
    # Remove from sessions
    if player_id in player_sessions:
        del player_sessions[player_id]
    
    # Delete room if empty
    if len(room["players"]) == 0:
        del rooms[room_id]
        return {"success": True, "message": "Left room (room deleted - was empty)"}
    
    # Transfer host if needed
    if room["host"] == player_id and len(room["players"]) > 0:
        room["host"] = room["players"][0]
        return {"success": True, "message": "Left room (host transferred)"}
    
    return {"success": True, "message": "Left room"}

@router.get("/health")
async def health():
    """Game service health check (no auth required)"""
    return {
        "status": "healthy",
        "service": "game",
        "active_rooms": len(rooms),
        "active_players": len(player_sessions)
    }