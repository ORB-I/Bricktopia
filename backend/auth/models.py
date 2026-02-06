# auth/models.py
from pydantic import BaseModel, Field
from typing import Optional

class SignupRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class PlayerResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str = ""
    user_id: Optional[str] = None
    coins: int = 0
    level: int = 1
    username: str = ""