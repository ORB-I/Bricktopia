@router.post("/create-room", response_model=RoomResponse)
async def create_room(request: CreateRoomRequest):
    """Create a new game room"""
    try:
        print(f"🎮 Creating room for player: {request.player_id}")
        
        # Fetch username from auth database
        player_result = supabase.table("players").select("username").eq("id", request.player_id).execute()
        username = player_result.data[0]["username"] if player_result.data else f"Player_{request.player_id[:8]}"
        
        room_id = str(uuid.uuid4())[:6].lower()
        
        rooms[room_id] = {
            "id": room_id,
            "host": request.player_id,
            "players": [
                {
                    "id": request.player_id,
                    "username": username
                }
            ],
            "created_at": time.time(),
            "state": {
                "scores": {},
                "started": False,
                "turn": 0
            }
        }
        player_sessions[request.player_id] = room_id
        
        print(f"✅ Room created: {room_id}")
        
        # Build usernames dictionary
        usernames = {request.player_id: username}
        
        return RoomResponse(
            success=True,
            room_id=room_id,
            photon_room=f"brick_{room_id}",
            players=[request.player_id],
            usernames=usernames  # Send usernames mapping
        )
        
    except Exception as e:
        print(f"❌ Error creating room: {e}")
        import traceback
        traceback.print_exc()
        return RoomResponse(
            success=False,
            error=f"Server error: {str(e)}"
        )

@router.post("/join-room", response_model=RoomResponse)
async def join_room(request: JoinRoomRequest):
    """Join existing room"""
    try:
        print(f"🎮 Player {request.player_id} joining room {request.room_id}")
        
        if request.room_id not in rooms:
            return RoomResponse(success=False, error="Room not found")
        
        room = rooms[request.room_id]
        
        # Check if player already in room
        for player in room["players"]:
            if player["id"] == request.player_id:
                # Build usernames mapping for all players
                usernames = {p["id"]: p["username"] for p in room["players"]}
                return RoomResponse(
                    success=True,
                    room_id=request.room_id,
                    photon_room=f"brick_{request.room_id}",
                    players=[p["id"] for p in room["players"]],
                    usernames=usernames
                )
        
        # Check room capacity
        if len(room["players"]) >= 8:
            return RoomResponse(success=False, error="Room full (max 8 players)")
        
        # Fetch username from auth database
        player_result = supabase.table("players").select("username").eq("id", request.player_id).execute()
        username = player_result.data[0]["username"] if player_result.data else f"Player_{request.player_id[:8]}"
        
        # Add player to room with username
        room["players"].append({
            "id": request.player_id,
            "username": username
        })
        player_sessions[request.player_id] = request.room_id
        
        # Build usernames mapping for all players
        usernames = {p["id"]: p["username"] for p in room["players"]}
        
        print(f"✅ Player joined. Room now has: {[p['username'] for p in room['players']]}")
        
        return RoomResponse(
            success=True,
            room_id=request.room_id,
            photon_room=f"brick_{request.room_id}",
            players=[p["id"] for p in room["players"]],
            usernames=usernames
        )
        
    except Exception as e:
        print(f"❌ Error joining room: {e}")
        return RoomResponse(
            success=False,
            error=f"Server error: {str(e)}"
        )

@router.get("/room/{room_id}")
async def get_room(room_id: str):
    """Get room info with usernames"""
    try:
        if room_id not in rooms:
            raise HTTPException(status_code=404, detail="Room not found")
        
        room = rooms[room_id]
        
        # Build usernames mapping
        usernames = {p["id"]: p["username"] for p in room["players"]}
        
        return {
            "success": True,
            "id": room["id"],
            "host": room["host"],
            "players": [p["id"] for p in room["players"]],
            "usernames": usernames,  # Add usernames here!
            "created_at": room["created_at"],
            "state": room["state"]
        }
        
    except Exception as e:
        print(f"❌ Error getting room: {e}")
        raise HTTPException(status_code=500, detail=str(e))