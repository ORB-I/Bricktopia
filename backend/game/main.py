from fastapi import FastAPI
import uuid
import time
from typing import Dict

app = FastAPI(title="Bricktopia Game Server")

# In-memory game state (Supabase for persistence later)
rooms: Dict[str, Dict] = {}
player_sessions: Dict[str, str] = {}  # player_id → room_id

@app.post("/create-room")
async def create_room(player_id: str):
    """Create a new game room"""
    room_id = str(uuid.uuid4())[:8]
    rooms[room_id] = {
        "id": room_id,
        "host": player_id,
        "players": [player_id],
        "created_at": time.time(),
        "state": {"scores": {}, "started": False}
    }
    player_sessions[player_id] = room_id
    
    return {
        "room_id": room_id,
        "photon_room": f"brick_{room_id}",
        "join_code": room_id  # Simple code for friends
    }

@app.post("/join-room")
async def join_room(room_id: str, player_id: str):
    """Join existing room"""
    if room_id not in rooms:
        return {"success": False, "error": "Room not found"}
    
    room = rooms[room_id]
    if len(room["players"]) >= 8:  # Max players
        return {"success": False, "error": "Room full"}
    
    room["players"].append(player_id)
    player_sessions[player_id] = room_id
    
    # Notify other players via Photon
    return {
        "success": True,
        "photon_room": f"brick_{room_id}",
        "players": room["players"]
    }

@app.post("/game-action")
async def game_action(player_id: str, action: str, data: Dict):
    """Process game action (move, shoot, etc.)"""
    room_id = player_sessions.get(player_id)
    if not room_id:
        return {"success": False, "error": "Not in a room"}
    
    # Update game state
    rooms[room_id]["state"]["last_action"] = {
        "player": player_id,
        "action": action,
        "data": data,
        "timestamp": time.time()
    }
    
    # Broadcast via Photon
    return {"success": True, "room_state": rooms[room_id]["state"]}

# Health check
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "active_rooms": len(rooms),
        "active_players": len(player_sessions)
    }