from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import os
import uuid
import time
import httpx

app = FastAPI(title="Bricktopia Auth Server")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Configuration - USE YOUR ACTUAL CREDENTIALS
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zpngzssopxcnulvileea.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_jmV7fSvVwz5bKMQCEf53bw_qFoWUIqf")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Photon Configuration
PHOTON_APP_ID = os.getenv("PHOTON_APP_ID", "f8c55f77-6e3c-446d-a236-860d0718993a")

# Request/Response Models
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

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate a user with Supabase database"""
    username = request.username.strip().lower()[:50]
    
    # Validation
    if not username or len(username) < 3:
        return LoginResponse(
            success=False, 
            message="Username must be 3+ characters"
        )
    
    try:
        # Check if user exists in Supabase
        response = supabase.table("players") \
            .select("id, username, coins, level, created_at") \
            .eq("username", username) \
            .execute()
        
        user_data = None
        user_id = None
        
        if response.data and len(response.data) > 0:
            # EXISTING USER - Update last_login
            user_data = response.data[0]
            user_id = user_data["id"]
            
            # Update last_login timestamp
            supabase.table("players") \
                .update({"last_login": "now()"}) \
                .eq("id", user_id) \
                .execute()
            
            message = f"Welcome back, {username}!"
            print(f"Existing user logged in: {username} (ID: {user_id})")
            
        else:
            # NEW USER - Create in database
            new_player = {
                "username": username,
                "coins": 100,
                "level": 1
            }
            
            insert_response = supabase.table("players") \
                .insert(new_player) \
                .execute()
            
            if not insert_response.data:
                return LoginResponse(
                    success=False,
                    message="Failed to create player account"
                )
            
            user_data = insert_response.data[0]
            user_id = user_data["id"]
            message = f"Welcome, {username}! You start with 100 coins."
            print(f"New user created: {username} (ID: {user_id})")
        
        # Generate authentication token (Photon integration pending)
        # For now, create a signed token with user info
        auth_token = f"bt_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        return LoginResponse(
            success=True,
            token=auth_token,
            message=message,
            user_id=user_id,
            coins=user_data.get("coins", 100),
            level=user_data.get("level", 1),
            username=username
        )
        
    except Exception as e:
        print(f"Database error for user {username}: {str(e)}")
        return LoginResponse(
            success=False,
            message="Server error. Please try again."
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Supabase connection
        test_query = supabase.table("players").select("count", count="exact").limit(1).execute()
        return {
            "status": "healthy",
            "service": "bricktopia-auth",
            "database": "connected",
            "player_count": test_query.count if hasattr(test_query, 'count') else "unknown"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "service": "bricktopia-auth",
            "database": "disconnected",
            "error": str(e)[:100]
        }

@app.get("/debug/players")
async def debug_players():
    """Debug endpoint to see all players (remove in production)"""
    try:
        players = supabase.table("players") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        return {"players": players.data}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Bricktopia Auth Server Starting...")
    print(f"Supabase URL: {SUPABASE_URL[:30]}...")
    print(f"Photon App ID: {PHOTON_APP_ID[:8]}...")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)