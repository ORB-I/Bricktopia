import os
import sys
import uuid
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# ===== ENVIRONMENT VARIABLES =====
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
PHOTON_APP_ID = os.getenv("PHOTON_APP_ID")

# Validate
if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    print("ERROR: Missing Supabase credentials in environment")
    print(f"SUPABASE_URL: {SUPABASE_URL}")
    print(f"SUPABASE_SERVICE_ROLE_KEY present: {bool(SUPABASE_SERVICE_ROLE_KEY)}")
    sys.exit(1)

# Initialize
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    print(f"✅ Connected to Supabase: {SUPABASE_URL[:30]}...")
except Exception as e:
    print(f"❌ Supabase init failed: {e}")
    sys.exit(1)

# ===== FASTAPI APP =====
app = FastAPI(title="Bricktopia Auth")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ===== MODELS =====
class LoginRequest(BaseModel):
    username: str

class LoginResponse(BaseModel):
    success: bool
    token: str = None
    message: str = ""
    user_id: str = None
    coins: int = 0
    level: int = 1
    username: str = ""

# ===== ROUTES =====
@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login EXISTING players only - fails if username doesn't exist"""
    username = request.username.strip().lower()
    
    if len(username) < 3:
        return LoginResponse(success=False, message="Username must be 3+ characters")
    
    try:
        # Find existing player
        result = supabase.table("players") \
            .select("*") \
            .eq("username", username) \
            .execute()
        
        if not result.data:
            return LoginResponse(
                success=False, 
                message="Account not found. Please sign up first."
            )
        
        player = result.data[0]
        
        # Update last_login
        supabase.table("players") \
            .update({"last_login": "now()"}) \
            .eq("id", player["id"]) \
            .execute()
        
        # Generate auth token
        auth_token = f"bt_login_{player['id']}_{int(time.time())}"
        
        return LoginResponse(
            success=True,
            token=auth_token,
            message=f"Welcome back, {username}!",
            user_id=player["id"],
            coins=player.get("coins", 100),
            level=player.get("level", 1),
            username=username
        )
        
    except Exception as e:
        print(f"Login error: {e}")
        return LoginResponse(success=False, message="Login failed")

@app.post("/signup", response_model=LoginResponse)
async def signup(request: LoginRequest):
    """Create a NEW player account - fails if username exists"""
    username = request.username.strip().lower()
    
    if len(username) < 3:
        return LoginResponse(success=False, message="Username must be 3+ characters")
    
    try:
        # Check if username already exists
        existing = supabase.table("players") \
            .select("id") \
            .eq("username", username) \
            .execute()
        
        if existing.data:
            return LoginResponse(
                success=False, 
                message="Username already taken. Try logging in instead."
            )
        
        # Create new player
        new_player = {
            "username": username,
            "coins": 100,
            "level": 1
        }
        
        result = supabase.table("players").insert(new_player).execute()
        player = result.data[0]
        
        # Generate auth token
        auth_token = f"bt_signup_{player['id']}_{int(time.time())}"
        
        return LoginResponse(
            success=True,
            token=auth_token,
            message=f"Welcome, {username}! Account created with 100 coins.",
            user_id=player["id"],
            coins=100,
            level=1,
            username=username
        )
        
    except Exception as e:
        print(f"Signup error: {e}")
        return LoginResponse(success=False, message="Account creation failed")


@app.get("/health")
async def health():
    return {"status": "ok", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)