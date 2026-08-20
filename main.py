import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from core.redis_config import redis_client
from custom_errors.user_existing_error import UserExistingError
from entities.users.exceptions import GitHubException
from entities import router
from managers import ConnectionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.ping()

    yield

    await redis_client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(router)

origins = [f"http://{os.getenv("FRONTEND_HOST")}:{os.getenv("FRONTEND_PORT")}"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory="media"), name="media")

manager = ConnectionManager()


@app.websocket("/ws/presence/{user_id}")
async def websocket_presence(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)


@app.exception_handler(UserExistingError)
async def user_existing_handler(request: Request, ext: UserExistingError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": ext.message}
    )


@app.exception_handler(GitHubException)
async def github_exception_handler(request: Request, exc: GitHubException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8030, reload=True)
