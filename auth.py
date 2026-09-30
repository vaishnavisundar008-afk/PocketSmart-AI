from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates

from app import database
from app.schemas import RegisterInput
from app.security import (
    SESSION_COOKIE,
    create_access_token,
    get_current_user,
    hash_password,
    issue_session_cookie,
    require_user,
    verify_password,
)


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _context(request: Request, **values) -> dict:
    return {"request": request, "csrf_token": request.state.csrf_token, **values}


@router.get("/register", name="register_page")
def register_page(request: Request, user: dict | None = Depends(get_current_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="auth.html",
        context=_context(request, mode="register", error=request.query_params.get("error")),
    )


@router.post("/register", name="register_user")
def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        details = RegisterInput(name=name, email=email, password=password)
    except Exception:
        return RedirectResponse("/register?error=invalid", status_code=303)
    user = database.create_user(details.name, details.email, hash_password(details.password))
    if not user:
        return RedirectResponse("/register?error=exists", status_code=303)
    response = RedirectResponse("/dashboard", status_code=303)
    issue_session_cookie(response, user["id"])
    return response


@router.get("/login", name="login_page")
def login_page(request: Request, user: dict | None = Depends(get_current_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="auth.html",
        context=_context(request, mode="login", error=request.query_params.get("error")),
    )


@router.post("/login", name="login_user")
def login_user(email: str = Form(...), password: str = Form(...)):
    user = database.get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return RedirectResponse("/login?error=invalid", status_code=303)
    response = RedirectResponse("/dashboard", status_code=303)
    issue_session_cookie(response, user["id"])
    return response


@router.post("/token")
def issue_token(form: OAuth2PasswordRequestForm = Depends()):
    user = database.get_user_by_email(form.username)
    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(user["id"]), "token_type": "bearer"}


@router.post("/logout", name="logout")
def logout(request: Request, csrf_token: str = Form(...)):
    import secrets

    cookie_token = request.cookies.get("pocketsmart_csrf", "")
    if not cookie_token or not secrets.compare_digest(cookie_token, csrf_token):
        raise HTTPException(status_code=403, detail="Refresh the page and try again.")
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/session-info")
def session_info(user: dict | None = Depends(get_current_user)):
    return {"authenticated": user is not None, "user_id": user["id"] if user else None}


@router.get("/session-data")
def session_data(user: dict = Depends(require_user)):
    return {
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
        "recommendation_count": database.count_recommendations(user["id"]),
        "recent": database.list_recommendations(user["id"], limit=5),
    }