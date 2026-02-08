# backend/main.py - COMPLETE FIXED VERSION
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Import routers
from auth.routes import router as auth_router
from game.routes import router as game_router

app = FastAPI(title="Bricktopia API", version="0.1.0")

# === CRITICAL CORS FIX ===
# When Electron makes requests from file:// or app:// origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow ALL origins for now
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Mount routers with prefixes
app.include_router(auth_router, prefix="/auth")
app.include_router(game_router, prefix="/game")

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
            }
        },
        "status": "online"
    }

# Global health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "bricktopia-api"}

# Simple test endpoint
@app.get("/test")
async def test():
    return {"message": "API is working!", "cors": "enabled"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)