import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.orchestrator import handle_chat
from app.retrieval.embed_store import CatalogStore
from app.schemas import ChatRequest, ChatResponse, HealthResponse

logger = logging.getLogger("shl_recommender")

store_holder: dict[str, CatalogStore] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    store_holder["store"] = CatalogStore()
    yield
    store_holder.clear()


app = FastAPI(title="SHL Assessment Recommender", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    store = store_holder.get("store")
    if store is None:
        return ChatResponse(
            reply="The service is still starting up, please try again in a moment.",
            recommendations=[],
            end_of_conversation=False,
        )
    return handle_chat(request.messages, store)


@app.exception_handler(Exception)
async def schema_safe_error_handler(request: Request, exc: Exception):
    raise exc