# main.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import os

# Import routers
from auth.routes import router as auth_router
from game.routes import router as game_router
from chat.server import handle_chat_connection

app = FastAPI(title="Bricktopia API", version="0.2.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router, prefix="/auth")
app.include_router(game_router, prefix="/game")

# WebSocket endpoint for chat
@app.websocket("/chat/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: str,
    username: str
):
    await handle_chat_connection(websocket, room_id, user_id, username)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Bricktopia API",
        "endpoints": {
            "auth": {
                "signup": "POST /auth/signup",
                "login": "POST /auth/login",
                "player": "GET /auth/player/{id}"
            },
            "game": {
                "create_room": "POST /game/create-room",
                "join_room": "POST /game/join-room",
                "game_action": "POST /game/game-action",
                "room_info": "GET /game/room/{id}"
            },
            "chat": {
                "websocket": "ws://your-server/chat/{room_id}?user_id={id}&username={name}"
            }
        },
        "status": "online"
    }