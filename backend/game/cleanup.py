# game/cleanup.py
import asyncio
import time
from typing import Dict

rooms: Dict[str, Dict] = {}
player_sessions: Dict[str, str] = {}

async def cleanup_old_rooms():
    """Background task to clean up inactive rooms"""
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        
        current_time = time.time()
        rooms_to_delete = []
        
        for room_id, room in list(rooms.items()):
            # Delete rooms older than 1 hour
            if current_time - room["created_at"] > 3600:
                rooms_to_delete.append(room_id)
                # Remove player sessions
                for player_id in room["players"]:
                    player_sessions.pop(player_id, None)
                print(f"Cleaned up old room: {room_id}")
        
        for room_id in rooms_to_delete:
            del rooms[room_id]

async def start_cleanup_task():
    """Start the cleanup task"""
    asyncio.create_task(cleanup_old_rooms())