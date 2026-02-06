from fastapi import APIRouter, HTTPException
from supabase import create_client
import os
import uuid
import time
from .models import LoginRequest, PlayerResponse

router = APIRouter()

# Initialize Supabase (shared with game module)
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

@router.post("/signup", response_model=PlayerResponse)
async def signup(request: LoginRequest):
    """Create NEW player account"""
    username = request.username.strip().lower()
    
    if len(username) < 3:
        return PlayerResponse(success=False, message="Username must be 3+ characters")
    
    try:
        # Check if username exists
        existing = supabase.table("players").select("id").eq("username", username).execute()
        if existing.data:
            return PlayerResponse(
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
        
        auth_token = f"bt_signup_{player['id']}_{int(time.time())}"
        
        return PlayerResponse(
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
        return PlayerResponse(success=False, message="Account creation failed")

@router.post("/login", response_model=PlayerResponse)
async def login(request: LoginRequest):
    """Login EXISTING player"""
    username = request.username.strip().lower()
    
    if len(username) < 3:
        return PlayerResponse(success=False, message="Username must be 3+ characters")
    
    try:
        # Find existing player
        result = supabase.table("players").select("*").eq("username", username).execute()
        if not result.data:
            return PlayerResponse(
                success=False, 
                message="Account not found. Please sign up first."
            )
        
        player = result.data[0]
        
        # Update last_login
        supabase.table("players").update({"last_login": "now()"}).eq("id", player["id"]).execute()
        
        auth_token = f"bt_login_{player['id']}_{int(time.time())}"
        
        return PlayerResponse(
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
        return PlayerResponse(success=False, message="Login failed")

@router.get("/player/{player_id}")
async def get_player(player_id: str):
    """Get player profile (used by game service)"""
    result = supabase.table("players").select("*").eq("id", player_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Player not found")
    return result.data[0]