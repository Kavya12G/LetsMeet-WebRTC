# from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# router = APIRouter()

# connected_peers = {}

# @router.websocket("/ws/signal/{client_id}")
# async def signaling(websocket: WebSocket, client_id: str):
#     await websocket.accept()
#     connected_peers[client_id] = websocket

#     try:
#         while True:
#             data = await websocket.receive_text()

#             # Forward message to other peer
#             for peer_id, peer_ws in connected_peers.items():
#                 if peer_id != client_id:
#                     await peer_ws.send_text(data)

#     except WebSocketDisconnect:
#         del connected_peers[client_id]

# ----------------------------------------------------------------------------------------------

# # Allowing multiuser to connect single room
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# room_id → { client_id: websocket }
rooms = {}

@router.websocket("/ws/signal/{room_id}/{client_id}")
async def signaling(websocket: WebSocket, room_id: str, client_id: str):
    await websocket.accept()

    if room_id not in rooms:
        rooms[room_id] = {}

    rooms[room_id][client_id] = websocket

    # Notify others that a new user joined
    for peer_id, peer_ws in rooms[room_id].items():
        if peer_id != client_id:
            await peer_ws.send_text(
                f'{{"new_user": "{client_id}"}}'
            )

    try:
        while True:
            data = await websocket.receive_text()

            # Forward signaling data to everyone else in room
            for peer_id, peer_ws in rooms[room_id].items():
                if peer_id != client_id:
                    await peer_ws.send_text(data)

    except WebSocketDisconnect:
        del rooms[room_id][client_id]

        # Notify others user left
        for peer_ws in rooms[room_id].values():
            await peer_ws.send_text(
                f'{{"user_left": "{client_id}"}}'
            )