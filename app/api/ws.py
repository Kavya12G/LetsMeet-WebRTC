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

rooms = {}           # room_id -> set(user_ids)
room_hosts = {}      # room_id -> host user_id
user_names = {}      # user_id -> username
user_rooms = {}      # user_id -> room_id
pending_removal: dict[int, asyncio.Task] = {}

# room_id -> {user_id -> {"event": asyncio.Event, "admitted": bool}}
waiting: dict[str, dict] = {}

GRACE_SECONDS = 8
ADMIT_TIMEOUT = 60


async def _remove_after_grace(user_id: int, room_id: str):
    await asyncio.sleep(GRACE_SECONDS)
    user_names.pop(user_id, None)
    user_rooms.pop(user_id, None)
    pending_removal.pop(user_id, None)
    if room_id in rooms:
        rooms[room_id].discard(user_id)
        if room_hosts.get(room_id) == user_id:
            remaining = list(rooms[room_id])
            if remaining:
                room_hosts[room_id] = remaining[0]
                await manager.send_to_user(remaining[0], {"type": "you_are_host"})
            else:
                room_hosts.pop(room_id, None)
        for peer_id in list(rooms[room_id]):
            await manager.send_to_user(peer_id, {"type": "user_left", "user_id": user_id})


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

    is_reconnect = user_id in pending_removal
    if is_reconnect:
        pending_removal[user_id].cancel()
        pending_removal.pop(user_id, None)

    if room_id not in rooms:
        rooms[room_id] = set()

    # ── Reconnect ──
    if is_reconnect and user_id in rooms[room_id]:
        for peer_id in list(rooms[room_id]):
            if peer_id != user_id:
                await manager.send_to_user(peer_id, {
                    "type": "peer_reconnected", "user_id": user_id, "username": username
                })
        existing = [uid for uid in rooms[room_id] if uid != user_id]
        await manager.send_to_user(user_id, {
            "type": "existing_users",
            "users": existing,
            "user_names": {str(uid): user_names.get(uid, str(uid)) for uid in existing},
            "my_id": user_id, "my_name": username,
            "is_reconnect": True, "is_host": room_hosts.get(room_id) == user_id
        })

    # ── First user → host, instant join ──
    elif not rooms[room_id]:
        rooms[room_id].add(user_id)
        user_rooms[user_id] = room_id
        room_hosts[room_id] = user_id
        await manager.send_to_user(user_id, {
            "type": "existing_users",
            "users": [], "user_names": {},
            "my_id": user_id, "my_name": username,
            "is_reconnect": False, "is_host": True
        })

    # ── Waiting room ──
    else:
        host_id = room_hosts.get(room_id)
        await manager.send_to_user(user_id, {
            "type": "waiting_admission", "my_id": user_id, "my_name": username
        })
        if host_id:
            await manager.send_to_user(host_id, {
                "type": "admission_request", "user_id": user_id, "username": username
            })

        entry = {"event": asyncio.Event(), "admitted": False}
        if room_id not in waiting:
            waiting[room_id] = {}
        waiting[room_id][user_id] = entry

        # Wait for host decision — keep socket alive, listen for cancel
        socket_closed = False
        async def _keep_alive():
            nonlocal socket_closed
            while not entry["event"].is_set():
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
                    msg = json.loads(raw)
                    if msg.get("type") == "cancel_wait":
                        entry["event"].set()
                        break
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    socket_closed = True
                    entry["event"].set()
                    break

        try:
            await asyncio.wait_for(_keep_alive(), timeout=float(ADMIT_TIMEOUT))
        except asyncio.TimeoutError:
            entry["event"].set()

        waiting.get(room_id, {}).pop(user_id, None)

        if socket_closed:
            manager.disconnect(user_id)
            return

        if not entry["admitted"]:
            try:
                await manager.send_to_user(user_id, {"type": "admission_denied"})
            except Exception:
                pass
            manager.disconnect(user_id)
            return
        # Admitted — full join
        existing = [{"user_id": uid, "username": user_names.get(uid, str(uid))} for uid in rooms[room_id]]
        await manager.send_to_user(user_id, {
            "type": "existing_users",
            "users": [u["user_id"] for u in existing],
            "user_names": {str(u["user_id"]): u["username"] for u in existing},
            "my_id": user_id, "my_name": username,
            "is_reconnect": False, "is_host": False
        })
        rooms[room_id].add(user_id)
        user_rooms[user_id] = room_id
        for peer_id in list(rooms[room_id]):
            if peer_id != user_id:
                await manager.send_to_user(peer_id, {
                    "type": "new_user", "user_id": user_id, "username": username
                })

    # ── Message loop ──
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            signal_type = message.get("type")

            if signal_type == "admit_user":
                target = int(message.get("user_id"))
                if room_id in waiting and target in waiting[room_id]:
                    waiting[room_id][target]["admitted"] = True
                    waiting[room_id][target]["event"].set()
                continue

            if signal_type == "deny_user":
                target = int(message.get("user_id"))
                if room_id in waiting and target in waiting[room_id]:
                    waiting[room_id][target]["admitted"] = False
                    waiting[room_id][target]["event"].set()
                continue

            if signal_type == "chat":
                for peer_id in list(rooms[room_id]):
                    if peer_id != user_id:
                        await manager.send_to_user(peer_id, {
                            "type": "chat", "from": user_id,
                            "from_name": username, "message": message.get("message")
                        })
                continue

            if signal_type == "media_state":
                for peer_id in list(rooms[room_id]):
                    if peer_id != user_id:
                        await manager.send_to_user(peer_id, {
                            "type": "media_state", "from": user_id,
                            "audio_muted": message.get("audio_muted"),
                            "video_off": message.get("video_off")
                        })
                continue

            target_user_id = message.get("target")
            signal_data = message.get("data")
            if target_user_id is not None:
                await manager.send_to_user(int(target_user_id), {
                    "from": user_id, "type": signal_type, "data": signal_data
                })

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        task = asyncio.create_task(_remove_after_grace(user_id, room_id))
        pending_removal[user_id] = task
