# game/routes.py - COMPLETE FIXED VERSION
from fastapi import APIRouter, HTTPException
from supabase import create_client
import os
import uuid
import time
from typing import Dict, List
from pydantic import BaseModel

# Local game models
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

router = APIRouter()

# Initialize Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# In-memory storage for rooms and chat
rooms: Dict[str, Dict] = {}
player_sessions: Dict[str, str] = {}  # player_id → room_id

# Chat messages storage
chat_messages: Dict[str, List[Dict]] = {}  # room_id → list of messages

@router.post("/create-room", response_model=RoomResponse)
async def create_room(request: CreateRoomRequest):
    """Create a new game room"""
    try:
        print(f"🎮 Creating room for player: {request.player_id}")
        
        # Fetch username from auth database
        player_result = supabase.table("players").select("username").eq("id", request.player_id).execute()
        username = player_result.data[0]["username"] if player_result.data else f"Player_{request.player_id[:8]}"
        
        room_id = str(uuid.uuid4())[:6].lower()
        
        rooms[room_id] = {
            "id": room_id,
            "host": request.player_id,
            "players": [
                {
                    "id": request.player_id,
                    "username": username
                }
            ],
            "created_at": time.time(),
            "state": {
                "scores": {},
                "started": False,
                "turn": 0
            }
        }
        player_sessions[request.player_id] = room_id
        
        # Initialize chat for this room
        chat_messages[room_id] = []
        
        print(f"✅ Room created: {room_id}")
        
        # Build usernames dictionary
        usernames = {request.player_id: username}
        
        return RoomResponse(
            success=True,
            room_id=room_id,
            photon_room=f"brick_{room_id}",
            players=[request.player_id],
            usernames=usernames
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
        for player in room["players"]:
            if player["id"] == request.player_id:
                # Build usernames mapping for all players
                usernames = {p["id"]: p["username"] for p in room["players"]}
                return RoomResponse(
                    success=True,
                    room_id=request.room_id,
                    photon_room=f"brick_{request.room_id}",
                    players=[p["id"] for p in room["players"]],
                    usernames=usernames
                )
        
        # Check room capacity
        if len(room["players"]) >= 8:
            return RoomResponse(success=False, error="Room full (max 8 players)")
        
        # Fetch username from auth database
        player_result = supabase.table("players").select("username").eq("id", request.player_id).execute()
        username = player_result.data[0]["username"] if player_result.data else f"Player_{request.player_id[:8]}"
        
        # Add player to room with username
        room["players"].append({
            "id": request.player_id,
            "username": username
        })
        player_sessions[request.player_id] = request.room_id
        
        # Build usernames mapping for all players
        usernames = {p["id"]: p["username"] for p in room["players"]}
        
        print(f"✅ Player joined. Room now has: {[p['username'] for p in room['players']]}")
        
        return RoomResponse(
            success=True,
            room_id=request.room_id,
            photon_room=f"brick_{request.room_id}",
            players=[p["id"] for p in room["players"]],
            usernames=usernames
        )
        
    except Exception as e:
        print(f"❌ Error joining room: {e}")
        return RoomResponse(
            success=False,
            error=f"Server error: {str(e)}"
        )

@router.get("/room/{room_id}")
async def get_room(room_id: str):
    """Get room info with usernames"""
    try:
        if room_id not in rooms:
            raise HTTPException(status_code=404, detail="Room not found")
        
        room = rooms[room_id]
        
        # Build usernames mapping
        usernames = {p["id"]: p["username"] for p in room["players"]}
        
        return {
            "success": True,
            "id": room["id"],
            "host": room["host"],
            "players": [p["id"] for p in room["players"]],
            "usernames": usernames,
            "created_at": room["created_at"],
            "state": room["state"]
        }
        
    except Exception as e:
        print(f"❌ Error getting room: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== CHAT ENDPOINTS =====
@router.post("/chat/send")
async def send_chat_message(data: dict):
    """Send a chat message to a room"""
    try:
        room_id = data.get("room_id")
        user_id = data.get("user_id")
        username = data.get("username")
        message = data.get("message", "").strip()
        
        if not room_id or not user_id or not username:
            return {"success": False, "error": "Missing required fields"}
        
        if not message:
            return {"success": False, "error": "Message cannot be empty"}
        
        # Limit message length
        if len(message) > 500:
            message = message[:500] + "..."
        
        # Create chat message
        chat_message = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "username": username,
            "message": message,
            "timestamp": time.time(),
            "type": "chat"
        }
        
        # Store message
        if room_id not in chat_messages:
            chat_messages[room_id] = []
        
        chat_messages[room_id].append(chat_message)
        
        # Keep only last 100 messages per room
        if len(chat_messages[room_id]) > 100:
            chat_messages[room_id] = chat_messages[room_id][-100:]
        
        print(f"💬 {username} in {room_id}: {message[:50]}...")
        
        return {"success": True, "message_id": chat_message["id"]}
        
    except Exception as e:
        print(f"❌ Error sending chat: {e}")
        return {"success": False, "error": str(e)}

@router.get("/chat/{room_id}")
async def get_chat_messages(room_id: str, after: float = 0, limit: int = 50):
    """Get chat messages for a room (polling endpoint)"""
    try:
        if room_id not in chat_messages:
            return {"success": True, "messages": [], "latest_timestamp": 0}
        
        # Filter messages after the given timestamp
        messages = chat_messages[room_id]
        new_messages = [msg for msg in messages if msg["timestamp"] > after]
        
        # Apply limit
        if len(new_messages) > limit:
            new_messages = new_messages[-limit:]
        
        # Get latest timestamp
        latest_timestamp = messages[-1]["timestamp"] if messages else 0
        
        return {
            "success": True,
            "messages": new_messages,
            "latest_timestamp": latest_timestamp
        }
        
    except Exception as e:
        print(f"❌ Error getting chat: {e}")
        return {"success": False, "error": str(e)}

@router.post("/chat/system")
async def send_system_message(data: dict):
    """Send a system message to a room"""
    try:
        room_id = data.get("room_id")
        message = data.get("message", "").strip()
        
        if not room_id or not message:
            return {"success": False, "error": "Missing required fields"}
        
        # Create system message
        system_message = {
            "id": str(uuid.uuid4()),
            "user_id": "system",
            "username": "System",
            "message": message,
            "timestamp": time.time(),
            "type": "system"
        }
        
        # Store message
        if room_id not in chat_messages:
            chat_messages[room_id] = []
        
        chat_messages[room_id].append(system_message)
        
        print(f"🔔 System message in {room_id}: {message}")
        
        return {"success": True, "message_id": system_message["id"]}
        
    except Exception as e:
        print(f"❌ Error sending system message: {e}")
        return {"success": False, "error": str(e)}

# ===== GAME ACTION ENDPOINTS =====
@router.post("/game-action")
async def game_action(request: GameActionRequest):
    """Handle game actions (move, shoot, build, etc.)"""
    try:
        player_id = request.player_id
        action = request.action
        data = request.data
        
        print(f"🎮 Game action: {action} from player {player_id}")
        
        # Find which room the player is in
        if player_id not in player_sessions:
            return {"success": False, "error": "Player not in any room"}
        
        room_id = player_sessions[player_id]
        
        if room_id not in rooms:
            return {"success": False, "error": "Room not found"}
        
        room = rooms[room_id]
        
        # Handle different game actions
        if action == "start_game":
            if player_id != room["host"]:
                return {"success": False, "error": "Only host can start the game"}
            
            room["state"]["started"] = True
            room["state"]["start_time"] = time.time()
            
            # Send system message
            system_message = {
                "id": str(uuid.uuid4()),
                "user_id": "system",
                "username": "System",
                "message": "Game started!",
                "timestamp": time.time(),
                "type": "system"
            }
            
            if room_id in chat_messages:
                chat_messages[room_id].append(system_message)
            
            return {"success": True, "message": "Game started"}
        
        elif action == "move":
            # Process player movement
            x = data.get("x", 0)
            y = data.get("y", 0)
            z = data.get("z", 0)
            
            return {
                "success": True,
                "action": "move",
                "player_id": player_id,
                "position": {"x": x, "y": y, "z": z}
            }
        
        elif action == "build":
            # Process building action
            block_type = data.get("block_type", "brick")
            x = data.get("x", 0)
            y = data.get("y", 0)
            z = data.get("z", 0)
            
            return {
                "success": True,
                "action": "build",
                "player_id": player_id,
                "block_type": block_type,
                "position": {"x": x, "y": y, "z": z}
            }
        
        elif action == "chat_emote":
            # Process emote
            emote = data.get("emote", "wave")
            
            # Add to chat messages as system/emote
            emote_message = {
                "id": str(uuid.uuid4()),
                "user_id": player_id,
                "username": "System",
                "message": f"*{player_id} {emote}s*",
                "timestamp": time.time(),
                "type": "emote"
            }
            
            if room_id in chat_messages:
                chat_messages[room_id].append(emote_message)
            
            return {"success": True, "emote": emote}
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
        
    except Exception as e:
        print(f"❌ Game action error: {e}")
        return {"success": False, "error": str(e)}

# ===== PLAYER MANAGEMENT =====
@router.post("/leave-room")
async def leave_room(data: dict):
    """Player leaves a room"""
    try:
        player_id = data.get("player_id")
        room_id = data.get("room_id")
        
        if not player_id or not room_id:
            return {"success": False, "error": "Missing player_id or room_id"}
        
        if room_id not in rooms:
            return {"success": False, "error": "Room not found"}
        
        room = rooms[room_id]
        
        # Remove player from room
        room["players"] = [p for p in room["players"] if p["id"] != player_id]
        
        # Remove player session
        if player_id in player_sessions:
            del player_sessions[player_id]
        
        # If room is empty, clean it up
        if len(room["players"]) == 0:
            del rooms[room_id]
            if room_id in chat_messages:
                del chat_messages[room_id]
            print(f"🗑️ Room {room_id} cleaned up (empty)")
        else:
            # If host left, assign new host
            if room["host"] == player_id and len(room["players"]) > 0:
                room["host"] = room["players"][0]["id"]
                print(f"👑 New host assigned: {room['host']}")
            
            # Add system message about player leaving
            system_message = {
                "id": str(uuid.uuid4()),
                "user_id": "system",
                "username": "System",
                "message": f"Player left the game",
                "timestamp": time.time(),
                "type": "system"
            }
            
            if room_id in chat_messages:
                chat_messages[room_id].append(system_message)
        
        return {"success": True, "message": "Left room successfully"}
        
    except Exception as e:
        print(f"❌ Leave room error: {e}")
        return {"success": False, "error": str(e)}

@router.get("/active-rooms")
async def get_active_rooms():
    """Get list of active rooms (for discovery)"""
    try:
        active_rooms = []
        
        for room_id, room in rooms.items():
            active_rooms.append({
                "room_id": room_id,
                "host": room["host"],
                "player_count": len(room["players"]),
                "max_players": 8,
                "created_at": room["created_at"],
                "game_started": room["state"]["started"]
            })
        
        return {
            "success": True,
            "rooms": active_rooms,
            "total_rooms": len(active_rooms)
        }
        
    except Exception as e:
        print(f"❌ Get active rooms error: {e}")
        return {"success": False, "error": str(e)}

@router.get("/health")
async def health():
    """Game service health check"""
    return {
        "status": "healthy",
        "service": "game",
        "active_rooms": len(rooms),
        "active_players": len(player_sessions),
        "active_chats": len(chat_messages)
    }