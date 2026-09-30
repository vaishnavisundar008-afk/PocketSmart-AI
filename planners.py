from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app import database
from app.schemas import HomeInput, JewelryInput, PartyInput
from app.security import require_csrf, require_user
from app.services.gemini import generate_plan


router = APIRouter()
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


@router.post("/generate-home")
def generate_home(
    payload: HomeInput,
    user: dict = Depends(require_user),
    _: None = Depends(require_csrf),
):
    request_data = payload.model_dump()
    result = generate_plan("home", request_data, payload.budget, payload.currency)
    database.save_recommendation(user["id"], "home", request_data, result)
    return result


@router.post("/generate-party")
def generate_party(
    payload: PartyInput,
    user: dict = Depends(require_user),
    _: None = Depends(require_csrf),
):
    request_data = payload.model_dump()
    result = generate_plan("party", request_data, payload.budget, payload.currency)
    database.save_recommendation(user["id"], "party", request_data, result)
    return result


@router.post("/generate-jewelry")
def generate_jewelry(
    budget: float = Form(..., gt=0, le=100_000_000),
    currency: str = Form("USD", pattern="^(USD|INR|EUR|GBP)$"),
    occasion: str = Form(..., min_length=2, max_length=60),
    style: str = Form(..., min_length=2, max_length=60),
    outfit_colors: str = Form("", max_length=120),
    image: UploadFile | None = File(None),
    user: dict = Depends(require_user),
    _: None = Depends(require_csrf),
):
    try:
        payload = JewelryInput(
            budget=budget,
            currency=currency,
            occasion=occasion,
            style=style,
            outfit_colors=outfit_colors,
        )
    except Exception as error:
        raise HTTPException(status_code=422, detail="Check the jewelry planner fields.") from error

    image_bytes = None
    image_mime = None
    if image and image.filename:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail="Upload a JPG, PNG, or WebP image.")
        image_bytes = image.file.read(MAX_IMAGE_BYTES + 1)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Outfit images must be 5 MB or smaller.")
        image_mime = image.content_type

    request_data = payload.model_dump()
    if image_bytes:
        request_data["outfit_image_attached"] = True
    result = generate_plan(
        "jewelry",
        request_data,
        payload.budget,
        payload.currency,
        image_bytes=image_bytes,
        image_mime=image_mime,
    )
    database.save_recommendation(user["id"], "jewelry", request_data, result)
    return result