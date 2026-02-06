from fastapi import FastAPI
from supabase import create_client
import os

app = FastAPI(title="Bricktopia Auth")

# Supabase for player data only
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

@app.post("/signup")
async def signup(username: str):
    """Create new player - auth service ONLY"""
    # Your existing signup logic
    pass

@app.post("/login") 
async def login(username: str):
    """Login existing player"""
    pass

@app.get("/player/{player_id}")
async def get_player(player_id: str):
    """Get player profile"""
    pass