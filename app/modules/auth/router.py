from fastapi import APIRouter, status, Depends
from app.core.email import send_email
from app.modules.auth.email_templates import (
    verification_email_template,
    reset_password_email_template,
)
from app.core.config import settings
from app.core.database import get_database
from .schemas import (
    RegisterSchema,
    LoginSchema,
    VerifyEmailSchema,
    ResendCodeSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
)
from .service import (
    register_user,
    login_user,
    verify_email_code,
    resend_verification_code,
    request_password_reset,
    reset_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterSchema, db=Depends(get_database)):
    result = await register_user(data, db)
    code = result.pop("verification_code")

    try:
        send_email(data.email, "Verifique sua conta Leaf Talk", verification_email_template(data.name, code))
    except Exception as exc:
        print(f"[EMAIL] verification send failed: {exc}")

    return result


@router.post("/login")
async def login(data: LoginSchema, db=Depends(get_database)):
    return await login_user(data, db)


@router.post("/verify-email")
async def verify_email(data: VerifyEmailSchema, db=Depends(get_database)):
    return await verify_email_code(data, db)


@router.post("/resend-code")
async def resend_code(data: ResendCodeSchema, db=Depends(get_database)):
    result = await resend_verification_code(data.email, db)

    if "code" in result:
        try:
            send_email(
                data.email,
                "Novo código de verificação Leaf Talk",
                verification_email_template(result.get("name", ""), result["code"]),
            )
        except Exception as exc:
            print(f"[EMAIL] resend verification failed: {exc}")

    return {"message": result["message"]}


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordSchema, db=Depends(get_database)):
    result = await request_password_reset(data.email, db)

    if "token" in result:
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={result['token']}"
        try:
            send_email(
                data.email,
                "Redefinição de senha Leaf Talk",
                reset_password_email_template(result.get("name", ""), reset_link),
            )
        except Exception as exc:
            print(f"[EMAIL] forgot password failed: {exc}")

    return {"message": result["message"]}


@router.post("/reset-password")
async def reset_password_endpoint(data: ResetPasswordSchema, db=Depends(get_database)):
    return await reset_password(data.token, data.password, db)
