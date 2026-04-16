from app.routes.job_description import router as jobs_router
from app.routes.interview       import router as interviews_router
from app.routes.analysis        import router as analysis_router
from app.routes.softskills      import router as softskills_router

__all__ = ["jobs_router", "interviews_router", "analysis_router", "softskills_router"]
