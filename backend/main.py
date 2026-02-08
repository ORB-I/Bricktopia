from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from friends.routes import router as friends_router
import os

# Import routers
from auth.routes import router as auth_router
from game.routes import router as game_router

app = FastAPI(title="Bricktopia API", version="0.1.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers with prefixes
app.include_router(auth_router, prefix="/auth")
app.include_router(game_router, prefix="/game")
app.include_router(friends_router, prefix="/friends")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Bricktopia API - BrickBackend V-3.0.14",
        "version": "0.1.0",
        "endpoints": {
            "auth": {
                "signup": "POST /auth/signup",
                "login": "POST /auth/login",
                "player": "GET /auth/player/{id}"
            },
            "game": {
                "create_room": "POST /game/create-room",
                "join_room": "POST /game/join-room",
                "room_info": "GET /game/room/{id}"
            },
            "friends": {
                "send_request": "POST /friends/send-request",
                "accept_request": "POST /friends/accept-request",
                "decline_request": "POST /friends/decline-request",
                "list": "GET /friends/list",
                "requests": "GET /friends/requests",
                "test": "GET /friends/test"
            }
        },
        "status": "online"
    }

# Global health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "bricktopia-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)