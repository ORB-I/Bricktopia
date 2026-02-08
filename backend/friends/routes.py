from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from auth.middleware import get_current_user
from supabase import create_client
import os

router = APIRouter()

# Initialize Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# ============ MODELS ============

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
        from_username = current_user["username"]
        to_username = request.to_username.strip().lower()
        
        print(f"[Friends] {from_username} -> {to_username}")
        
        # Can't send request to yourself
        if from_username.lower() == to_username:
            return FriendResponse(
                success=False, 
                error="You cannot send a friend request to yourself"
            )
        
        # Find target user
        target_result = supabase.table("players").select("id, username").eq("username", to_username).execute()
        if not target_result.data:
            return FriendResponse(
                success=False, 
                error=f"User '{to_username}' not found"
            )
        
        to_user_id = target_result.data[0]["id"]
        to_username = target_result.data[0]["username"]
        
        print(f"[Friends] Target found: {to_user_id} ({to_username})")
        
        # Check if already friends
        existing_friend = supabase.table("friends").select("*").match({
            "user_id": from_user_id,
            "friend_id": to_user_id
        }).execute()
        
        if existing_friend.data:
            return FriendResponse(
                success=False, 
                error=f"You are already friends with {to_username}"
            )
        
        # Check if request already exists (pending)
        existing_request = supabase.table("friend_requests").select("*").match({
            "from_user": from_user_id,
            "to_user": to_user_id,
            "status": "pending"
        }).execute()
        
        if existing_request.data:
            return FriendResponse(
                success=False, 
                error="Friend request already sent"
            )
        
        # Check if THEY sent YOU a request (reverse check)
        reverse_request = supabase.table("friend_requests").select("*").match({
            "from_user": to_user_id,
            "to_user": from_user_id,
            "status": "pending"
        }).execute()
        
        if reverse_request.data:
            return FriendResponse(
                success=False, 
                error=f"{to_username} already sent you a friend request! Check your incoming requests."
            )
        
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
        
        result = supabase.table("friend_requests").insert(friend_request).execute()
        
        print(f"[Friends] Request created: {request_id}")
        
        return FriendResponse(
            success=True,
            request_id=request_id,
            error=None
        )
        
    except Exception as e:
        print(f"[Friends] Send request error: {e}")
        import traceback
        traceback.print_exc()
        return FriendResponse(success=False, error="Server error: " + str(e))

@router.post("/accept-request", response_model=FriendResponse)
async def accept_friend_request(
    request: AcceptRequest,
    current_user: dict = Depends(get_current_user)
):
    """Accept a friend request"""
    try:
        user_id = current_user["user_id"]
        username = current_user["username"]
        request_id = request.request_id
        
        print(f"[Friends] {username} accepting request {request_id}")
        
        # Get the request
        request_result = supabase.table("friend_requests").select("*").match({
            "id": request_id,
            "to_user": user_id,
            "status": "pending"
        }).execute()
        
        if not request_result.data:
            return FriendResponse(
                success=False, 
                error="Friend request not found, already processed, or doesn't belong to you"
            )
        
        friend_request = request_result.data[0]
        from_user_id = friend_request["from_user"]
        
        # Get sender's username for logging
        sender_result = supabase.table("players").select("username").eq("id", from_user_id).execute()
        sender_username = sender_result.data[0]["username"] if sender_result.data else "Unknown"
        
        # Create friendship (both directions)
        now = datetime.utcnow().isoformat()
        
        # Add user A → user B (you → them)
        supabase.table("friends").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "friend_id": from_user_id,
            "status": "accepted",
            "accepted_at": now
        }).execute()
        
        # Add user B → user A (them → you) - reciprocal
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
        
        print(f"[Friends] {username} and {sender_username} are now friends!")
        
        return FriendResponse(success=True)
        
    except Exception as e:
        print(f"[Friends] Accept request error: {e}")
        import traceback
        traceback.print_exc()
        return FriendResponse(success=False, error="Server error: " + str(e))

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
        
        print(f"[Friends] Request {request_id} declined by user {user_id}")
        
        return FriendResponse(success=True)
        
    except Exception as e:
        print(f"[Friends] Decline request error: {e}")
        return FriendResponse(success=False, error="Server error: " + str(e))

@router.get("/list", response_model=FriendResponse)
async def get_friends(current_user: dict = Depends(get_current_user)):
    """Get user's friends list"""
    try:
        user_id = current_user["user_id"]
        username = current_user["username"]
        
        print(f"[Friends] Getting friends for {username} ({user_id})")
        
        # Get friends with usernames and basic info
        # Note: Supabase foreign key syntax can be tricky. Let's do it in two queries if needed.
        
        # First get friend IDs
        friends_result = supabase.table("friends").select("friend_id").eq("user_id", user_id).eq("status", "accepted").execute()
        
        if not friends_result.data:
            print(f"[Friends] No friends found for {username}")
            return FriendResponse(
                success=True,
                friends=[]
            )
        
        friend_ids = [friend["friend_id"] for friend in friends_result.data]
        
        # Get friend details
        friends_details = []
        for friend_id in friend_ids:
            player_result = supabase.table("players").select("id, username, coins, level, created_at").eq("id", friend_id).execute()
            if player_result.data:
                friend_info = player_result.data[0]
                # Add friendship metadata
                friendship = supabase.table("friends").select("accepted_at").match({
                    "user_id": user_id,
                    "friend_id": friend_id
                }).execute()
                
                friends_details.append({
                    "friend": friend_info,
                    "status": "accepted",
                    "accepted_at": friendship.data[0]["accepted_at"] if friendship.data else None
                })
        
        print(f"[Friends] Found {len(friends_details)} friends for {username}")
        
        return FriendResponse(
            success=True,
            friends=friends_details
        )
        
    except Exception as e:
        print(f"[Friends] Get friends error: {e}")
        import traceback
        traceback.print_exc()
        return FriendResponse(success=False, error="Server error: " + str(e), friends=[])

@router.get("/requests", response_model=FriendResponse)
async def get_friend_requests(current_user: dict = Depends(get_current_user)):
    """Get pending friend requests"""
    try:
        user_id = current_user["user_id"]
        username = current_user["username"]
        
        print(f"[Friends] Getting requests for {username}")
        
        # Get incoming requests
        # We'll do a simpler approach: get requests and then fetch sender info
        requests_result = supabase.table("friend_requests").select("*").eq("to_user", user_id).eq("status", "pending").execute()
        
        if not requests_result.data:
            print(f"[Friends] No pending requests for {username}")
            return FriendResponse(
                success=True,
                requests=[]
            )
        
        requests_with_senders = []
        for req in requests_result.data:
            # Get sender info
            sender_result = supabase.table("players").select("id, username, created_at").eq("id", req["from_user"]).execute()
            sender_info = sender_result.data[0] if sender_result.data else {"username": "Unknown"}
            
            requests_with_senders.append({
                "id": req["id"],
                "from_user": sender_info,
                "message": req["message"],
                "created_at": req["created_at"]
            })
        
        print(f"[Friends] Found {len(requests_with_senders)} pending requests for {username}")
        
        return FriendResponse(
            success=True,
            requests=requests_with_senders
        )
        
    except Exception as e:
        print(f"[Friends] Get requests error: {e}")
        import traceback
        traceback.print_exc()
        return FriendResponse(success=False, error="Server error: " + str(e), requests=[])

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify friends API is working"""
    return {
        "success": True,
        "message": "BrickFriends API is operational! 🧱👥",
        "endpoints": {
            "send_request": "POST /friends/send-request",
            "accept_request": "POST /friends/accept-request", 
            "decline_request": "POST /friends/decline-request",
            "list": "GET /friends/list",
            "requests": "GET /friends/requests"
        }
    }