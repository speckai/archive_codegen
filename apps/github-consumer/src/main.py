from contextlib import asynccontextmanager

# import tracemalloc
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from src.config import DEV
from src.github_router import router as github_router
from src.utils.dev_utils import spawn_smee_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DEV:
        await spawn_smee_client()
    yield


app: FastAPI = FastAPI(
    title="GitHub Consumer",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

app.include_router(github_router)

if DEV:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
async def root():
    return RedirectResponse(url="https://speck.sh")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
