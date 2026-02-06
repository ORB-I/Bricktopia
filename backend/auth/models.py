# backend/auth/models.py
from pydantic import BaseModel, field_validator

class SignupRequest(BaseModel):
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        v = v.strip().lower()
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 20:
            raise ValueError('Username must be at most 20 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v
    
    @field_validator('password')
    @classmethod
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        if len(v) > 100:
            raise ValueError('Password too long')
        return v

class LoginRequest(BaseModel):
    username: str
    password: str

class PlayerResponse(BaseModel):
    success: bool
    token: str = None
    message: str = ""
    user_id: str = None
    coins: int = 0
    level: int = 1
    username: str = ""

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    coins: int
    level: int