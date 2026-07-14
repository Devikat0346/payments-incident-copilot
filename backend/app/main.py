import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.poller import Poller
from app.state import state

poller = Poller(state)


@asynccontextmanager
async def lifespan(app: FastAPI):
    poller.start()
    yield
    poller.stop()


app = FastAPI(title="Payments Incident Copilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/cases")
async def cases(limit: int = 50):
    return [c.to_dict() for c in state.recent_cases(limit)]


@app.get("/api/cases/{case_id}")
async def case_detail(case_id: str):
    case = state.cases.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="not found")
    return case.to_dict()


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    state.subscribers.add(queue)
    try:
        for case in state.recent_cases(20):
            await websocket.send_json({"type": "case_opened", "data": case.to_dict()})
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        state.subscribers.discard(queue)
