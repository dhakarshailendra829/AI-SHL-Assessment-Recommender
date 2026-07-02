import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.orchestrator import handle_chat
from app.retrieval.embed_store import CatalogStore
from app.schemas import ChatRequest, ChatResponse, HealthResponse

logger = logging.getLogger("shl_recommender")

store_holder: dict[str, CatalogStore | None] = {"store": None}

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="SHL Assessment Recommender", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if store_holder["store"] is None:
        store_holder["store"] = CatalogStore()

    return handle_chat(request.messages, store_holder["store"])

@app.exception_handler(Exception)
async def schema_safe_error_handler(request: Request, exc: Exception):
    raise exc