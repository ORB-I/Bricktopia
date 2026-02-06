from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str

class PlayerResponse(BaseModel):
    success: bool
    token: str = None
    message: str = ""
    user_id: str = None
    coins: int = 0
    level: int = 1
    username: str = ""