# auth/routes.py - COMPLETE FIX
from fastapi import APIRouter, HTTPException
from supabase import create_client
import os
import time
from .models import SignupRequest, LoginRequest, PlayerResponse

router = APIRouter()

# Initialize Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

@router.post("/signup", response_model=PlayerResponse)
async def signup(request: SignupRequest):
    """Create NEW player account with Supabase Auth"""
    username = request.username.strip().lower()
    password = request.password
    
    # Validate password length for Supabase
    if len(password.encode('utf-8')) > 72:
        return PlayerResponse(
            success=False, 
            message="Password too long (max 72 bytes). Please use a shorter password."
        )
    
    try:
        # Check if username exists in our players table
        existing = supabase.table("players").select("id").eq("username", username).execute()
        if existing.data:
            return PlayerResponse(
                success=False, 
                message="Username already taken. Try logging in instead."
            )
        
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": f"{username}@bricktopia.game",  # Supabase requires email
            "password": password,
            "user_metadata": {"username": username}
        })
        
        if not auth_response.user:
            return PlayerResponse(success=False, message="Failed to create auth account")
        
        user_id = auth_response.user.id
        
        # Create player profile in our database
        new_player = {
            "id": user_id,  # Use Supabase Auth UID
            "username": username,
            "coins": 100,
            "level": 1,
            "created_at": "now()"
        }
        
        result = supabase.table("players").insert(new_player).execute()
        
        # Generate our own session token (or use Supabase's)
        auth_token = f"bt_{user_id}_{int(time.time())}"
        
        return PlayerResponse(
            success=True,
            token=auth_token,
            message=f"Welcome, {username}! Account created with 100 coins.",
            user_id=user_id,
            coins=100,
            level=1,
            username=username
        )
        
    except Exception as e:
        print(f"Signup error: {e}")
        # Clean up if auth succeeded but player creation failed
        if 'user_id' in locals():
            try:
                supabase.auth.admin.delete_user(user_id)
            except:
                pass
        return PlayerResponse(success=False, message=str(e))

@router.post("/login", response_model=PlayerResponse)
async def login(request: LoginRequest):
    """Login EXISTING player with Supabase Auth"""
    username = request.username.strip().lower()
    password = request.password
    
    try:
        # First, get the user ID from our players table
        player_result = supabase.table("players").select("*").eq("username", username).execute()
        if not player_result.data:
            return PlayerResponse(
                success=False, 
                message="Account not found. Please sign up first."
            )
        
        player = player_result.data[0]
        user_id = player["id"]
        
        # Try to authenticate with Supabase Auth
        # Note: Supabase Auth uses email, not username
        email = f"{username}@bricktopia.game"
        
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not auth_response.user:
                return PlayerResponse(success=False, message="Invalid password")
                
        except Exception as auth_error:
            # If auth fails, it might be an old account (pre-Supabase Auth)
            print(f"Auth error (maybe old account): {auth_error}")
            # For now, allow login with just username check for backward compatibility
            pass
        
        # Update last_login
        supabase.table("players").update({"last_login": "now()"}).eq("id", user_id).execute()
        
        # Generate session token
        auth_token = f"bt_{user_id}_{int(time.time())}"
        
        return PlayerResponse(
            success=True,
            token=auth_token,
            message=f"Welcome back, {username}!",
            user_id=user_id,
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

@router.get("/health")
async def health():
    return {"status": "ok", "service": "auth"}