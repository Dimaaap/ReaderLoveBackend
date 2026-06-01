from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from core.redis_config import redis_client
from entities import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.ping()

    yield

    await redis_client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8030, reload=True)
