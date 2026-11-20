from fastapi import WebSocket


class ConnectionManager:

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self.latest_clipboard: str = ""


    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        if self.latest_clipboard :
            await websocket.send_text(self.latest_clipboard)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)


    async def broadcast(self, message: str) -> None:
        self.latest_clipboard = message

        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)
