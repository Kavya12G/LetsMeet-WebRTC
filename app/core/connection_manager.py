class ConnectionManager:
    def __init__(self):
        self.active_connections = {}  # client_id -> websocket

    async def connect(self, client_id, websocket):
        self.active_connections[str(client_id)] = websocket

    def disconnect(self, client_id, websocket=None):
        key = str(client_id)
        if key in self.active_connections:
            del self.active_connections[key]

    async def send_to_user(self, client_id, message: dict):
        key = str(client_id)
        print(f"[send_to_user] target={key}, active_keys={list(self.active_connections.keys())}, msg_type={message.get('type')}")
        if key in self.active_connections:
            ws = self.active_connections[key]
            try:
                await ws.send_json(message)
                print(f"[send_to_user] sent to {key} OK")
            except Exception as e:
                print(f"[send_to_user] Error sending to {key}: {e}")
        else:
            print(f"[send_to_user] MISS — {key} not in active_connections")