# backend/friends/routes.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from auth.middleware import get_current_user
from supabase import create_client
import os

router = APIRouter()
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# ============ MODELS ============
from pydantic import BaseModel

class FriendRequest(BaseModel):
    to_username: str
    message: Optional[str] = ""

class AcceptRequest(BaseModel):
    request_id: str

class FriendResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    friends: Optional[List[Dict]] = []
    requests: Optional[List[Dict]] = []
    request_id: Optional[str] = None

# ============ ENDPOINTS ============

@router.post("/send-request", response_model=FriendResponse)
async def send_friend_request(
    request: FriendRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a friend request to another user"""
    try:
        from_user_id = current_user["user_id"]
        to_username = request.to_username.strip().lower()
        
        # Can't send request to yourself
        if current_user["username"].lower() == to_username:
            return FriendResponse(success=False, error="Cannot send friend request to yourself")
        
        # Find target user
        target_result = supabase.table("players").select("id, username").eq("username", to_username).execute()
        if not target_result.data:
            return FriendResponse(success=False, error="User not found")
        
        to_user_id = target_result.data[0]["id"]
        
        # Check if already friends
        existing_friend = supabase.table("friends").select("*").match({
            "user_id": from_user_id,
            "friend_id": to_user_id
        }).execute()
        
        if existing_friend.data:
            return FriendResponse(success=False, error="Already friends with this user")
        
        # Check if request already exists
        existing_request = supabase.table("friend_requests").select("*").match({
            "from_user": from_user_id,
            "to_user": to_user_id,
            "status": "pending"
        }).execute()
        
        if existing_request.data:
            return FriendResponse(success=False, error="Friend request already sent")
        
        # Create friend request
        request_id = str(uuid.uuid4())
        friend_request = {
            "id": request_id,
            "from_user": from_user_id,
            "to_user": to_user_id,
            "message": request.message or "",
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("friend_requests").insert(friend_request).execute()
        
        return FriendResponse(
            success=True,
            request_id=request_id,
            error=None
        )
        
    except Exception as e:
        print(f"Send friend request error: {e}")
        return FriendResponse(success=False, error=str(e))

@router.post("/accept-request", response_model=FriendResponse)
async def accept_friend_request(
    request: AcceptRequest,
    current_user: dict = Depends(get_current_user)
):
    """Accept a friend request"""
    try:
        user_id = current_user["user_id"]
        request_id = request.request_id
        
        # Get the request
        request_result = supabase.table("friend_requests").select("*").match({
            "id": request_id,
            "to_user": user_id,
            "status": "pending"
        }).execute()
        
        if not request_result.data:
            return FriendResponse(success=False, error="Friend request not found or already processed")
        
        friend_request = request_result.data[0]
        from_user_id = friend_request["from_user"]
        
        # Create friendship (both directions)
        now = datetime.utcnow().isoformat()
        
        # Add user A → user B
        supabase.table("friends").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "friend_id": from_user_id,
            "status": "accepted",
            "accepted_at": now
        }).execute()
        
        # Add user B → user A (reciprocal)
        supabase.table("friends").insert({
            "id": str(uuid.uuid4()),
            "user_id": from_user_id,
            "friend_id": user_id,
            "status": "accepted",
            "accepted_at": now
        }).execute()
        
        # Update request status
        supabase.table("friend_requests").update({
            "status": "accepted",
            "processed_at": now
        }).eq("id", request_id).execute()
        
        return FriendResponse(success=True)
        
    except Exception as e:
        print(f"Accept friend request error: {e}")
        return FriendResponse(success=False, error=str(e))

@router.post("/decline-request", response_model=FriendResponse)
async def decline_friend_request(
    request: AcceptRequest,
    current_user: dict = Depends(get_current_user)
):
    """Decline a friend request"""
    try:
        user_id = current_user["user_id"]
        request_id = request.request_id
        
        # Update request status
        supabase.table("friend_requests").update({
            "status": "declined",
            "processed_at": datetime.utcnow().isoformat()
        }).match({
            "id": request_id,
            "to_user": user_id,
            "status": "pending"
        }).execute()
        
        return FriendResponse(success=True)
        
    except Exception as e:
        print(f"Decline friend request error: {e}")
        return FriendResponse(success=False, error=str(e))

@router.get("/list", response_model=FriendResponse)
async def get_friends(current_user: dict = Depends(get_current_user)):
    """Get user's friends list"""
    try:
        user_id = current_user["user_id"]
        
        # Get friends with usernames
        friends_result = supabase.table("friends").select(
            """
            friend:players!friends_friend_id_fkey (
                id,
                username,
                avatar_url,
                level,
                coins
            ),
            status,
            accepted_at
            """
        ).eq("user_id", user_id).eq("status", "accepted").execute()
        
        return FriendResponse(
            success=True,
            friends=friends_result.data or []
        )
        
    except Exception as e:
        print(f"Get friends error: {e}")
        return FriendResponse(success=False, error=str(e), friends=[])

@router.get("/requests", response_model=FriendResponse)
async def get_friend_requests(current_user: dict = Depends(get_current_user)):
    """Get pending friend requests"""
    try:
        user_id = current_user["user_id"]
        
        # Get incoming requests with sender info
        requests_result = supabase.table("friend_requests").select(
            """
            *,
            from_user:players!friend_requests_from_user_fkey (
                id,
                username,
                avatar_url
            )
            """
        ).eq("to_user", user_id).eq("status", "pending").execute()
        
        return FriendResponse(
            success=True,
            requests=requests_result.data or []
        )
        
    except Exception as e:
        print(f"Get friend requests error: {e}")
        return FriendResponse(success=False, error=str(e), requests=[])

# Optional: Remove friend endpoint
@router.post("/remove")
async def remove_friend(friend_id: str, current_user: dict = Depends(get_current_user)):
    """Remove a friend"""
    try:
        user_id = current_user["user_id"]
        
        # Remove both directions
        supabase.table("friends").delete().match({
            "user_id": user_id,
            "friend_id": friend_id
        }).execute()
        
        supabase.table("friends").delete().match({
            "user_id": friend_id,
            "friend_id": user_id
        }).execute()
        
        return {"success": True}
        
    except Exception as e:
        return {"success": False, "error": str(e)}