import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from core.redis_config import redis_client
from custom_errors.user_existing_error import UserExistingError
from entities import router


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
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(UserExistingError)
async def user_existing_handler(request: Request, ext: UserExistingError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": ext.message}
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8030, reload=True)
