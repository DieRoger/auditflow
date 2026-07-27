"""WebSocket — Workflow 实时事件推送"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, workflow_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(workflow_id, []).append(ws)

    def disconnect(self, workflow_id: str, ws: WebSocket):
        conns = self._connections.get(workflow_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, workflow_id: str, event: dict):
        """向指定 Workflow 的所有订阅者推送事件"""
        for ws in self._connections.get(workflow_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/api/v1/ws/workflows/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket 端点 — 订阅 Workflow 实时事件"""
    await manager.connect(workflow_id, websocket)
    try:
        while True:
            # 保持连接（接收客户端 ping）
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(workflow_id, websocket)
