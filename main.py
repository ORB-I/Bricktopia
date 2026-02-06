from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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
        users_db[username] = str(uuid.uuid4())
    
    user_id = users_db[username]
    
    try:
        # FIXED INDENTATION BELOW
        auth_url = "https://auth.photonengine.com/auth/token"
        
        # CORRECT payload structure for Photon
        auth_payload = {
            "UserId": user_id,
            "Nickname": username,
            "AppId": PHOTON_APP_ID,
            "AppVersion": PHOTON_APP_VERSION,
            "Region": PHOTON_REGION if PHOTON_REGION else "eu"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                auth_url,
                json=auth_payload,
                headers=headers,
                timeout=10.0
            )
            
            print(f"Photon Response Status: {response.status_code}")
            print(f"Photon Response Body: {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                photon_token = token_data.get("Token") or token_data.get("token") or token_data.get("AccessToken")
                
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
                        message=f"Photon response missing token. Full response: {token_data}"
                    )
            else:
                return LoginResponse(
                    success=False,
                    message=f"Photon API error {response.status_code}: {response.text}"
                )
                
    except httpx.ConnectError as e:
        return LoginResponse(
            success=False,
            message=f"Cannot connect to Photon servers: {str(e)}"
        )
    except Exception as e:
        return LoginResponse(
            success=False,
            message=f"Server error: {str(e)}"
        )

@app.post("/mock-login", response_model=LoginResponse)
async def mock_login(request: LoginRequest):
    """MOCK endpoint for immediate testing"""
    username = request.username.strip()
    
    if not username:
        return LoginResponse(success=False, message="Username required")
    
    if username not in users_db:
        users_db[username] = str(uuid.uuid4())[:8]
    
    user_id = users_db[username]
    
    # Realistic mock token format
    import time, random
    mock_token = f"mock_{user_id}_{int(time.time())}_{random.randint(1000,9999)}"
    
    return LoginResponse(
        success=True,
        token=mock_token,
        message=f"Welcome {username}! (Photon auth pending)",
        user_id=user_id
    )

@app.get("/mock-test")
async def mock_test_page():
    """Serve a simple HTML test page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Photon Mock Test</title>
        <style>
            body { font-family: Arial; padding: 30px; max-width: 500px; margin: 0 auto; }
            input, button { padding: 10px; font-size: 16px; margin: 5px; }
            #result { background: #f5f5f5; padding: 15px; margin-top: 20px; border-radius: 5px; white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <h2>🔐 Photon Login Test (Mock Mode)</h2>
        <input id="username" placeholder="Enter username" value="TestPlayer">
        <button onclick="login()">Get Mock Token</button>
        
        <h3>Connection Test:</h3>
        <button onclick="testConnection()">Test Server Connection</button>
        
        <div id="result"></div>
        
        <script>
        async function login() {
            const username = document.getElementById('username').value;
            const result = document.getElementById('result');
            result.textContent = 'Requesting token...';
            
            try {
                const response = await fetch('/mock-login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: username})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    result.innerHTML = `✅ <b>SUCCESS!</b><br>
                                       User ID: ${data.user_id}<br>
                                       Mock Token:<br>
                                       <code style="word-break: break-all">${data.token}</code><br><br>
                                       <i>Photon integration pending...</i>`;
                } else {
                    result.innerHTML = `❌ Error: ${data.message}`;
                }
            } catch (error) {
                result.innerHTML = `❌ Network error: ${error.message}`;
            }
        }
        
        async function testConnection() {
            const result = document.getElementById('result');
            result.textContent = 'Testing server connection...';
            
            try {
                const response = await fetch('/health');
                const data = await response.json();
                result.innerHTML = `✅ <b>Server is online!</b><br>
                                   Status: ${data.status}<br>
                                   Service: ${data.service}`;
            } catch (error) {
                result.innerHTML = `❌ Server connection failed: ${error.message}`;
            }
        }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/health")
async def health_check():
    """Simple health endpoint to verify server is running"""
    return {"status": "ok", "service": "game-auth-server"}

if __name__ == "__main__":
    import uvicorn
    print(f"Server starting... Photon App ID: {PHOTON_APP_ID[:8]}...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
