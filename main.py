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
    """Real Supabase authentication - NO MOCK"""
    username = request.username.strip().lower()
    
    if len(username) < 3:
        return LoginResponse(success=False, message="Username too short")
    
    try:
        # Check existing user
        result = supabase.table("players").select("*").eq("username", username).execute()
        
        if result.data:
            # Existing user
            user = result.data[0]
            user_id = user["id"]
            
            # Update last_login
            supabase.table("players").update({"last_login": "now()"}).eq("id", user_id).execute()
            
            return LoginResponse(
                success=True,
                token=f"bt_{user_id}_{int(time.time())}",
                message=f"Welcome back, {username}!",
                user_id=user_id,
                coins=user.get("coins", 100),
                level=user.get("level", 1),
                username=username
            )
        else:
            # New user
            new_user = {
                "username": username,
                "coins": 100,
                "level": 1
            }
            
            insert_result = supabase.table("players").insert(new_user).execute()
            user = insert_result.data[0]
            user_id = user["id"]
            
            return LoginResponse(
                success=True,
                token=f"bt_{user_id}_{int(time.time())}",
                message=f"Welcome, {username}! You have 100 coins.",
                user_id=user_id,
                coins=100,
                level=1,
                username=username
            )
            
    except Exception as e:
        print(f"Database error: {e}")
        return LoginResponse(success=False, message="Database error")

@app.get("/health")
async def health():
    return {"status": "ok", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)