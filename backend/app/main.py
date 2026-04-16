from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.job_description import router as jobs_router
from app.routes.interview       import router as interviews_router
from app.routes.analysis        import router as analysis_router
from app.routes.softskills      import router as softskills_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("[Startup] Loading video models...")
    try:
        from app.analysis_pipeline.video.emotion_detector import _load_models
        _load_models()
        print("[Startup] Video models ready")
    except Exception as e:
        print(f"[Startup] Video models failed: {e} — video module disabled")

    print("[Startup] Ready")
    yield


app = FastAPI(title="AI Analyzer API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router,       prefix="/api/v1")
app.include_router(interviews_router, prefix="/api/v1")
app.include_router(analysis_router,   prefix="/api/v1")
app.include_router(softskills_router, prefix="/api/v1")