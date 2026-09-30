from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import database
from app.security import get_current_user, require_user


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
PLANNERS = {
    "home": {"title": "Home planner", "eyebrow": "ROOM BY ROOM", "description": "Make space for the pieces that matter, without losing sight of the total."},
    "party": {"title": "Party planner", "eyebrow": "BRING PEOPLE TOGETHER", "description": "Give food, venue and atmosphere a sensible share of the budget."},
    "jewelry": {"title": "Jewelry planner", "eyebrow": "THE FINISHING DETAIL", "description": "Build a coordinated look for the occasion and leave a little room to breathe."},
}


def _context(request: Request, **values) -> dict:
    return {"request": request, "csrf_token": request.state.csrf_token, **values}


def _login_redirect():
    return RedirectResponse("/login", status_code=303)


@router.get("/", name="home_page")
def home_page(request: Request, user: dict | None = Depends(get_current_user)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=_context(request, user=user),
    )


@router.get("/dashboard", name="dashboard")
def dashboard(request: Request, user: dict | None = Depends(get_current_user)):
    if not user:
        return _login_redirect()
    recent = database.list_recommendations(user["id"], limit=4)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_context(request, user=user, recent=recent, count=database.count_recommendations(user["id"])),
    )


@router.get("/planner/{kind}", name="planner_page")
def planner_page(kind: str, request: Request, user: dict | None = Depends(get_current_user)):
    if kind not in PLANNERS:
        return RedirectResponse("/dashboard", status_code=303)
    if not user:
        return _login_redirect()
    return templates.TemplateResponse(
        request=request,
        name="planner.html",
        context=_context(request, user=user, planner=kind, content=PLANNERS[kind]),
    )


@router.get("/history", name="history_page")
def history_page(request: Request, user: dict | None = Depends(get_current_user)):
    if not user:
        return _login_redirect()
    entries = database.list_recommendations(user["id"])
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context=_context(request, user=user, entries=entries),
    )


@router.get("/testimonials", name="testimonials")
def testimonials(request: Request, user: dict | None = Depends(get_current_user)):
    return templates.TemplateResponse(
        request=request,
        name="testimonials.html",
        context=_context(request, user=user),
    )


@router.get("/recommendations-details/{entry_id}", name="recommendation_details")
def recommendation_details(
    entry_id: str,
    request: Request,
    user: dict | None = Depends(get_current_user),
):
    if not user:
        return _login_redirect()
    entry = database.get_recommendation(user["id"], entry_id)
    if not entry:
        return RedirectResponse("/history", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="detail.html",
        context=_context(request, user=user, entry=entry),
    )


@router.get("/api/history")
def history_api(user: dict = Depends(require_user)):
    return {"items": database.list_recommendations(user["id"])}