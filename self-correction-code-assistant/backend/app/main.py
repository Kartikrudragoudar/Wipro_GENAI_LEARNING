import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import HealthResponse
from app.routes import analyze, graph, self_correct, upload

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "Self-Correction Code Assistant API"),
    description="Loop Engineering backend with LangGraph agent workflow, embeddings, file upload, and LLM providers.",
    version="0.4.0",
)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(self_correct.router)
app.include_router(upload.router)
app.include_router(graph.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="self-correction-code-assistant", provider=os.getenv("AI_PROVIDER", "mock"))
