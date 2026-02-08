# backend/main.py - WITH ERROR HANDLING
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

app = FastAPI(title="Bricktopia API", version="0.1.0")

# === GLOBAL ERROR HANDLER ===
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global error: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers INSIDE try-except
try:
    from auth.routes import router as auth_router
    from game.routes import router as game_router
    app.include_router(auth_router, prefix="/auth")
    app.include_router(game_router, prefix="/game")
    print("✅ Routers loaded successfully")
except Exception as e:
    print(f"❌ Failed to load routers: {e}")
    traceback.print_exc()
    # Create simple test endpoints
    @app.post("/auth/login")
    async def test_login():
        return {"success": False, "message": "Auth router failed to load"}
    
    @app.post("/auth/signup")
    async def test_signup():
        return {"success": False, "message": "Auth router failed to load"}

# Test endpoint
@app.get("/")
async def root():
    return {"status": "online", "message": "Bricktopia API"}

@app.get("/test")
async def test():
    return {"test": "ok", "cors": "working"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, access_log=True)