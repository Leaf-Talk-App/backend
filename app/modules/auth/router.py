from fastapi import APIRouter, status
from .schemas import RegisterSchema, LoginSchema
from .service import register_user, login_user
from app.core.email import send_email
from app.modules.auth.email_templates import verification_email_template
from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
async def register(data: RegisterSchema):
    user = await register_user(data)

    # Usando o ID real do usuário salvo no banco para gerar o token
    token = create_access_token({"sub": str(user.id)})

    verification_link = (
        f"{settings.FRONTEND_URL}"
        f"/verify-email?token={token}"
    )

    html = verification_email_template(
        data.name,
        verification_link
    )

    send_email(
        data.email,
        "Verify your account",
        html
    )

    return user

@router.post("/login")
async def login(data: LoginSchema):
    return await login_user(data)