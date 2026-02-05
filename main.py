from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uuid

app = FastAPI(title="Game Auth Server")

# Allow Godot web client to call this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this later for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Photon Configuration
PHOTON_APP_ID = "f8c55f77-6e3c-446d-a236-860d0718993a"
PHOTON_APP_VERSION = "1.0"  # Your app version
PHOTON_REGION = "eu"  # Change to "us", "asia", etc. as needed

# Request/Response models
class LoginRequest(BaseModel):
    username: str

class LoginResponse(BaseModel):
    success: bool
    token: str = None
    message: str = ""
    user_id: str = None

# In-memory "database" for prototype (replace with real DB later)
users_db = {}

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate a user and get a Photon token"""
    username = request.username.strip()
    
    if not username:
        return LoginResponse(success=False, message="Username required")
    
    # Create or get user ID
    if username not in users_db:
        users_db[username] = str(uuid.uuid4())[:8]  # Simple user ID
    
    user_id = users_db[username]
    
    try:
        # Step 1: Get Photon authentication token via REST API
        async with httpx.AsyncClient() as client:
            # Photon's token authentication endpoint
            auth_url = f"https://api.photonengine.com/{PHOTON_APP_ID}/auth/token"
            
            # Request body for Photon
            auth_payload = {
                "UserId": user_id,
                "Nickname": username,
                "TitleId": PHOTON_APP_ID,
                "AppVersion": PHOTON_APP_VERSION,
            }
            
            headers = {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            }
            
            response = await client.post(
                auth_url,
                json=auth_payload,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                token_data = response.json()
                photon_token = token_data.get("Token")
                
                if photon_token:
                    return LoginResponse(
                        success=True,
                        token=photon_token,
                        message=f"Welcome {username}!",
                        user_id=user_id
                    )
                else:
                    return LoginResponse(
                        success=False,
                        message="Photon didn't return a valid token"
                    )
            else:
                return LoginResponse(
                    success=False,
                    message=f"Photon error: {response.status_code} - {response.text}"
                )
                
    except Exception as e:
        return LoginResponse(
            success=False,
            message=f"Server error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Simple health endpoint to verify server is running"""
    return {"status": "ok", "service": "game-auth-server"}

if __name__ == "__main__":
    import uvicorn
    print(f"Server starting... Photon App ID: {PHOTON_APP_ID[:8]}...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
