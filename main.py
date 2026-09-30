import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app import database
from app.config import settings
from app.routes import auth, pages, planners


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize_database()
    yield


app = FastAPI(
    title="PocketSmart AI",
    description="Budget-aware planning for home, gatherings and occasion styling.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(planners.router)


@app.middleware("http")
async def csrf_cookie(request: Request, call_next):
    token = request.cookies.get("pocketsmart_csrf") or secrets.token_urlsafe(32)
    request.state.csrf_token = token
    response = await call_next(request)
    if not request.cookies.get("pocketsmart_csrf"):
        response.set_cookie(
            "pocketsmart_csrf",
            token,
            max_age=60 * 60 * 24 * 30,
            httponly=False,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
        )
    return response


@app.get("/startup", tags=["system"])
def startup_status():
    return {"status": "ready", "gemini_configured": bool(settings.gemini_api_key)}


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.exception_handler(404)
async def not_found(_: Request, __):
    return JSONResponse(status_code=404, content={"detail": "This page could not be found."})