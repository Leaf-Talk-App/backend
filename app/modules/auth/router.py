from fastapi import APIRouter, status, Depends
from .schemas import RegisterSchema, LoginSchema
from .service import register_user, login_user
from app.core.email import send_email
from app.modules.auth.email_templates import verification_email_template
from app.core.config import settings
from app.core.security import create_access_token
from app.core.database import get_database

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
async def register(
    data: RegisterSchema,
    db = Depends(get_database)
):
    user = await register_user(data, db)

    token = create_access_token({
        "sub": str(user["id"])
    })

    verification_link = (
        f"{settings.FRONTEND_URL}"
        f"/verify-email?token={token}"
    )

    html = verification_email_template(
        data.name,
        verification_link
    )

    try:
        send_email(
            data.email,
            "Verify your account",
            html
        )
    except Exception as e:
        print(
            "Aviso: Não foi possível enviar "
            f"o e-mail de verificação. Erro: {e}"
        )

    return user


@router.post("/login")
async def login(
    data: LoginSchema,
    db = Depends(get_database)
):
    return await login_user(data, db)