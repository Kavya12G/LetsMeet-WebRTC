from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.security import decode_token
from app.models.user import User
from app.core.connection_manager import ConnectionManager
import json
import asyncio

router = APIRouter()
manager = ConnectionManager()

# room_id -> set(user_ids)
rooms = {}

# user_id -> username
user_names = {}

# user_id -> room_id  (so we can restore on reconnect)
user_rooms = {}

# user_id -> asyncio.Task  (pending removal task during grace period)
pending_removal: dict[int, asyncio.Task] = {}

GRACE_SECONDS = 8   # seconds to wait before treating a disconnect as permanent


async def _remove_after_grace(user_id: int, room_id: str):
    """Remove user from room after grace period if they haven't reconnected."""
    await asyncio.sleep(GRACE_SECONDS)
    # Still disconnected — do the real cleanup
    user_names.pop(user_id, None)
    user_rooms.pop(user_id, None)
    pending_removal.pop(user_id, None)
    if room_id in rooms:
        rooms[room_id].discard(user_id)
        for peer_id in list(rooms[room_id]):
            await manager.send_to_user(
                peer_id,
                {"type": "user_left", "user_id": user_id}
            )
    print(f"User {user_id} permanently removed from room {room_id} after grace period")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    token = websocket.query_params.get("token")
    room_id = websocket.query_params.get("room")

    if not token or not room_id:
        await websocket.close(code=1008)
        return

    payload = decode_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    user_id = int(payload.get("sub"))

    db: Session = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()

    if not user:
        await websocket.close(code=1008)
        return

    username = user.username
    user_names[user_id] = username

    await websocket.accept()
    await manager.connect(user_id, websocket)

    # ── Reconnect: cancel pending removal if user comes back within grace period ──
    is_reconnect = user_id in pending_removal
    if is_reconnect:
        pending_removal[user_id].cancel()
        pending_removal.pop(user_id, None)
        print(f"User {user_id} ({username}) reconnected to room {room_id}")

    if room_id not in rooms:
        rooms[room_id] = set()

    if is_reconnect and user_id in rooms[room_id]:
        # Already in room — just tell peers to re-negotiate with this user
        for peer_id in list(rooms[room_id]):
            if peer_id != user_id:
                await manager.send_to_user(
                    peer_id,
                    {"type": "peer_reconnected", "user_id": user_id, "username": username}
                )
        # Tell the reconnected user who is in the room so they can re-negotiate
        existing = [uid for uid in rooms[room_id] if uid != user_id]
        await manager.send_to_user(
            user_id,
            {
                "type": "existing_users",
                "users": existing,
                "user_names": {str(uid): user_names.get(uid, str(uid)) for uid in existing},
                "my_id": user_id,
                "my_name": username,
                "is_reconnect": True
            }
        )
    else:
        # Fresh join
        existing = [
            {"user_id": uid, "username": user_names.get(uid, str(uid))}
            for uid in rooms[room_id]
        ]

        await manager.send_to_user(
            user_id,
            {
                "type": "existing_users",
                "users": [u["user_id"] for u in existing],
                "user_names": {str(u["user_id"]): u["username"] for u in existing},
                "my_id": user_id,
                "my_name": username,
                "is_reconnect": False
            }
        )

        # Add new user to room AFTER sending existing_users
        rooms[room_id].add(user_id)
        user_rooms[user_id] = room_id

        print(f"User {user_id} ({username}) joined room {room_id}. Room: {rooms[room_id]}")

        # Tell everyone already in the room about the new user
        for peer_id in list(rooms[room_id]):
            if peer_id != user_id:
                await manager.send_to_user(
                    peer_id,
                    {"type": "new_user", "user_id": user_id, "username": username}
                )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            signal_type = message.get("type")

            if signal_type == "chat":
                chat_message = message.get("message")
                for peer_id in list(rooms[room_id]):
                    if peer_id != user_id:
                        await manager.send_to_user(
                            peer_id,
                            {
                                "type": "chat",
                                "from": user_id,
                                "from_name": username,
                                "message": chat_message
                            }
                        )
                continue

            if signal_type == "media_state":
                for peer_id in list(rooms[room_id]):
                    if peer_id != user_id:
                        await manager.send_to_user(
                            peer_id,
                            {
                                "type": "media_state",
                                "from": user_id,
                                "audio_muted": message.get("audio_muted"),
                                "video_off": message.get("video_off")
                            }
                        )
                continue

            target_user_id = message.get("target")
            signal_data = message.get("data")

            await manager.send_to_user(
                int(target_user_id),
                {
                    "from": user_id,
                    "type": signal_type,
                    "data": signal_data
                }
            )

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        print(f"User {user_id} disconnected — starting {GRACE_SECONDS}s grace period")
        # Schedule removal after grace period (cancelled if user reconnects in time)
        task = asyncio.create_task(_remove_after_grace(user_id, room_id))
        pending_removal[user_id] = task
