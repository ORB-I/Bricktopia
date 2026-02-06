# backend/auth/routes.py
from fastapi import APIRouter, HTTPException, Depends
from supabase import create_client
import os
from .models import SignupRequest, LoginRequest, PlayerResponse, TokenResponse
from .utils import hash_password, verify_password, create_access_token
from .middleware import get_current_user

router = APIRouter()

# Initialize Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest):
    """Create NEW player account with password"""
    username = request.username.strip().lower()
    password = request.password
    
    try:
        # Check if username exists
        existing = supabase.table("players").select("id").eq("username", username).execute()
        if existing.data:
            raise HTTPException(
                status_code=400,
                detail="Username already taken"
            )
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create new player
        new_player = {
            "username": username,
            "password_hash": password_hash,
            "coins": 100,
            "level": 1
        }
        
        result = supabase.table("players").insert(new_player).execute()
        player = result.data[0]
        
        # Create JWT token
        access_token = create_access_token(player["id"], username)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=player["id"],
            username=username,
            coins=100,
            level=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Account creation failed")

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login EXISTING player with password verification"""
    username = request.username.strip().lower()
    password = request.password
    
    try:
        # Find existing player
        result = supabase.table("players").select("*").eq("username", username).execute()
        if not result.data:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        player = result.data[0]
        
        # Verify password
        if not verify_password(password, player.get("password_hash", "")):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Update last_login
        supabase.table("players").update({
            "last_login": "now()"
        }).eq("id", player["id"]).execute()
        
        # Create JWT token
        access_token = create_access_token(player["id"], username)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=player["id"],
            username=username,
            coins=player.get("coins", 100),
            level=player.get("level", 1)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.get("/me")
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile (requires auth)"""
    user_id = current_user["user_id"]
    
    result = supabase.table("players").select(
        "id, username, coins, level, created_at, last_login"
    ).eq("id", user_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return result.data[0]

@router.get("/player/{player_id}")
async def get_player(
    player_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get player profile by ID (requires auth)
    Only returns public info unless requesting own profile
    """
    requester_id = current_user["user_id"]
    
    # Query player
    result = supabase.table("players").select(
        "id, username, level, created_at"
    ).eq("id", player_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player = result.data[0]
    
    # If requesting own profile, include private data
    if player_id == requester_id:
        full_result = supabase.table("players").select(
            "id, username, coins, level, created_at, last_login"
        ).eq("id", player_id).execute()
        player = full_result.data[0]
    
    return player

@router.post("/verify")
async def verify_token_endpoint(current_user: dict = Depends(get_current_user)):
    """Verify if a token is valid (useful for client-side token validation)"""
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "username": current_user["username"]
    }

@router.get("/health")
async def auth_health():
    """Auth service health check (no auth required)"""
    return {
        "status": "healthy",
        "service": "auth"
    }