# backend/auth/routes.py
from fastapi import APIRouter, HTTPException
from supabase import create_client
import os
import uuid
import time
import hashlib
from .models import SignupRequest, LoginRequest, PlayerResponse

router = APIRouter()

# Initialize Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

@router.post("/signup", response_model=PlayerResponse)
async def signup(request: SignupRequest):
    """Create NEW player account"""
    username = request.username.strip().lower()
    password = request.password
    
    # Validate inputs
    if len(username) < 3:
        return PlayerResponse(
            success=False, 
            message="Username must be at least 3 characters"
        )
    
    try:
        # Check if username exists
        existing = supabase.table("players").select("id").eq("username", username).execute()
        if existing.data:
            return PlayerResponse(
                success=False, 
                message="Username already taken. Try logging in instead."
            )
        
        # Create new player WITH SHA256 HASH
        player_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        new_player = {
            "id": player_id,
            "username": username,
            "password_hash": password_hash,
            "coins": 100,
            "level": 1,
            "created_at": "now()"
        }
        
        result = supabase.table("players").insert(new_player).execute()
        
        if not result.data:
            return PlayerResponse(success=False, message="Failed to create player")
            
        # Generate session token
        auth_token = f"bt_{player_id}_{int(time.time())}"
        
        return PlayerResponse(
            success=True,
            token=auth_token,
            message=f"Welcome, {username}! Account created with 100 coins.",
            user_id=player_id,
            coins=100,
            level=1,
            username=username
        )
        
    except Exception as e:
        print(f"Signup error: {e}")
        import traceback
        traceback.print_exc()
        return PlayerResponse(success=False, message="Account creation failed")

@router.post("/login", response_model=PlayerResponse)
async def login(request: LoginRequest):
    """Login EXISTING player"""
    username = request.username.strip().lower()
    password = request.password
    
    try:
        print(f"[Auth] Login attempt for: {username}")
        
        # Find player by username
        result = supabase.table("players").select("*").eq("username", username).execute()
        
        if not result.data:
            print(f"[Auth] User not found: {username}")
            return PlayerResponse(
                success=False, 
                message="Account not found. Please sign up first."
            )
        
        player = result.data[0]
        print(f"[Auth] Found player: {player['id']}")
        
        # Check password
        stored_hash = player.get("password_hash", "")
        provided_hash = hashlib.sha256(password.encode()).hexdigest()
        
        print(f"[Auth] Stored hash: {stored_hash[:20]}...")
        print(f"[Auth] Provided hash: {provided_hash[:20]}...")
        
        if provided_hash != stored_hash:
            # Try plain text fallback
            if password[:50] != stored_hash:
                print(f"[Auth] Password mismatch for {username}")
                return PlayerResponse(
                    success=False, 
                    message="Invalid password"
                )
        
        # Update last_login
        supabase.table("players").update({"last_login": "now()"}).eq("id", player["id"]).execute()
        
        # Generate session token
        auth_token = f"bt_{player['id']}_{int(time.time())}"
        
        print(f"[Auth] Login successful for {username}")
        
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
        import traceback
        traceback.print_exc()
        return PlayerResponse(success=False, message="Login failed")

@router.get("/player/{player_id}")
async def get_player(player_id: str):
    """Get player profile"""
    result = supabase.table("players").select("*").eq("id", player_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Player not found")
    return result.data[0]

@router.get("/health")
async def health():
    return {"status": "ok", "service": "auth"}

@router.get("/test")
async def test_auth():
    return {"status": "auth router working"}

@router.post("/test-login")
async def test_login_endpoint(request: dict):
    """Test endpoint that accepts raw dict"""
    print(f"Test login received: {request}")
    return {
        "success": True,
        "message": "Test endpoint works",
        "received_data": request
    }