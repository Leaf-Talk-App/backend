from pydantic import BaseModel, EmailStr, field_validator

class RegisterSchema(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("O nome deve ter pelo menos 2 caracteres")
        return v.strip()

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("A senha deve ter pelo menos 6 caracteres")
        if not any(c.isupper() for c in v):
            raise ValueError("A senha deve conter uma letra maiúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("A senha deve conter um número")
        return v

class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailSchema(BaseModel):
    code: str
    email: EmailStr | None = None


class ResendCodeSchema(BaseModel):
    email: EmailStr


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str
    password: str


class GoogleCodeSchema(BaseModel):
    code: str
    redirect_uri: str


class GoogleTokenSchema(BaseModel):
    id_token: str
