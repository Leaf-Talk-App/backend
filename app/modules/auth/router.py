from fastapi import APIRouter, status, Depends, BackgroundTasks
from urllib.parse import urlencode
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
    GoogleCodeSchema,
    GoogleTokenSchema,
)
from .service import (
    register_user,
    login_user,
    verify_email_code,
    resend_verification_code,
    request_password_reset,
    reset_password,
    exchange_google_code,
    login_or_create_google_user,
    verify_google_id_token,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterSchema, background_tasks: BackgroundTasks, db=Depends(get_database)):
    result = await register_user(data, db)
    code = result.pop("verification_code")

    # E-mail em background → cadastro responde na hora (SMTP não bloqueia o request)
    background_tasks.add_task(
        send_email,
        data.email,
        "Verifique sua conta Leaf Talk",
        verification_email_template(data.name, code),
    )

    return result


@router.post("/login")
async def login(data: LoginSchema, db=Depends(get_database)):
    return await login_user(data, db)


@router.post("/verify-email")
async def verify_email(data: VerifyEmailSchema, db=Depends(get_database)):
    return await verify_email_code(data, db)


@router.post("/resend-code")
async def resend_code(data: ResendCodeSchema, background_tasks: BackgroundTasks, db=Depends(get_database)):
    result = await resend_verification_code(data.email, db)

    if "code" in result:
        background_tasks.add_task(
            send_email,
            data.email,
            "Novo código de verificação Leaf Talk",
            verification_email_template(result.get("name", ""), result["code"]),
        )

    return {"message": result["message"]}


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordSchema, background_tasks: BackgroundTasks, db=Depends(get_database)):
    result = await request_password_reset(data.email, db)

    if "token" in result:
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={result['token']}"
        background_tasks.add_task(
            send_email,
            data.email,
            "Redefinição de senha Leaf Talk",
            reset_password_email_template(result.get("name", ""), reset_link),
        )

    return {"message": result["message"]}


@router.post("/reset-password")
async def reset_password_endpoint(data: ResetPasswordSchema, db=Depends(get_database)):
    return await reset_password(data.token, data.password, db)


@router.get("/google/url")
async def google_auth_url(redirect_uri: str | None = None):
    if not settings.GOOGLE_CLIENT_ID:
        return {"url": None}

    final_redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI or settings.FRONTEND_URL
    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": final_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "include_granted_scopes": "true",
            "prompt": "select_account",
        }
    )
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
    return {"url": url}


@router.post("/google/exchange")
async def google_exchange(data: GoogleCodeSchema, db=Depends(get_database)):
    google_profile = await exchange_google_code(data.code, data.redirect_uri)
    return await login_or_create_google_user(google_profile, db)


@router.post("/google/token")
async def google_token_login(data: GoogleTokenSchema, db=Depends(get_database)):
    google_profile = verify_google_id_token(data.id_token)
    return await login_or_create_google_user(google_profile, db)
