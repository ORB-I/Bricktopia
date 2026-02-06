# backend/auth/middleware.py
from fastapi import Header, HTTPException, Depends
from typing import Optional
from .utils import verify_token

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Verify JWT token from Authorization header and return user data
    
    Usage in routes:
        @router.post("/endpoint")
        async def endpoint(current_user: dict = Depends(get_current_user)):
            user_id = current_user["user_id"]
            username = current_user["username"]
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )
    
    # Handle "Bearer <token>" format
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    # Verify token
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    
    return payload

async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Optional auth - returns user if token valid, None otherwise
    Useful for endpoints that work with or without auth
    """
    if not authorization:
        return None
    
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    return verify_token(token)