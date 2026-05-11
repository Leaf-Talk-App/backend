from fastapi import APIRouter, status
from .schemas import RegisterSchema, LoginSchema
from .service import register_user, login_user
from app.core.email import send_email
from app.modules.auth.email_templates import verification_email_template
from app.core.config import settings

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
async def register(data: RegisterSchema):
    return await register_user(data)

@router.post("/login")
async def login(data: LoginSchema):
    return await login_user(data)

verification_link = (
    f"{settings.FRONTEND_URL}"
    f"/verify-email?token={token}"
)

html = verification_email_template(
    user["name"],
    verification_link
)

send_email(
    user["email"],
    "Verify your account",
    html
)