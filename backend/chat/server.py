# chat/server.py
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_rooms: Dict[str, str] = {}  # user_id -> room_id
        
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, username: str):
        await websocket.accept()
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        
        self.active_connections[room_id].add(websocket)
        self.user_rooms[user_id] = room_id
        
        logger.info(f"📨 {username} joined chat for room {room_id}")
        
        # Send join notification to room
        join_message = {
            "type": "system",
            "user_id": "system",
            "username": "System",
            "message": f"{username} joined the chat",
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(room_id, join_message, exclude=websocket)
        
        # Send room history
        history_message = {
            "type": "history",
            "messages": self.get_room_history(room_id)
        }
        await websocket.send_text(json.dumps(history_message))
    
    def disconnect(self, websocket: WebSocket, room_id: str, user_id: str, username: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            if len(self.active_connections[room_id]) == 0:
                del self.active_connections[room_id]
        
        if user_id in self.user_rooms:
            del self.user_rooms[user_id]
        
        logger.info(f"📨 {username} left chat for room {room_id}")
        
        # Send leave notification
        leave_message = {
            "type": "system",
            "user_id": "system",
            "username": "System",
            "message": f"{username} left the chat",
            "timestamp": asyncio.get_event_loop().time()
        }
        asyncio.create_task(self.broadcast(room_id, leave_message))
    
    async def broadcast(self, room_id: str, message: dict, exclude: WebSocket = None):
        if room_id not in self.active_connections:
            return
        
        message_json = json.dumps(message)
        for connection in self.active_connections[room_id]:
            if connection != exclude:
                try:
                    await connection.send_text(message_json)
                except:
                    pass
    
    async def send_private(self, user_id: str, message: dict):
        # Could implement private messaging later
        pass
    
    def get_room_history(self, room_id: str) -> list:
        # In production, store in database. For now, return empty
        return []

chat_manager = ChatManager()

# In-memory message storage (replace with Redis/DB in production)
message_history: Dict[str, list] = {}

async def handle_chat_connection(websocket: WebSocket, room_id: str, user_id: str, username: str):
    await chat_manager.connect(websocket, room_id, user_id, username)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Validate message
            if "message" not in message_data or not message_data["message"].strip():
                continue
            
            # Construct chat message
            chat_message = {
                "type": "chat",
                "user_id": user_id,
                "username": username,
                "message": message_data["message"].strip(),
                "timestamp": asyncio.get_event_loop().time(),
                "color": message_data.get("color", "#ffffff")
            }
            
            # Store in history
            if room_id not in message_history:
                message_history[room_id] = []
            message_history[room_id].append(chat_message)
            
            # Keep last 100 messages
            if len(message_history[room_id]) > 100:
                message_history[room_id] = message_history[room_id][-100:]
            
            # Broadcast to room
            await chat_manager.broadcast(room_id, chat_message)
            
            logger.info(f"💬 {username}: {chat_message['message'][:50]}...")
            
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, room_id, user_id, username)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        chat_manager.disconnect(websocket, room_id, user_id, username)