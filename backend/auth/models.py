# auth/models.py
from pydantic import BaseModel, Field

class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=3, max_length=72)  # Max 72 bytes for Supabase

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=3, max_length=72)

class PlayerResponse(BaseModel):
    success: bool
    token: str = None
    message: str = ""
    user_id: str = None
    coins: int = 0
    level: int = 1
    username: str = ""