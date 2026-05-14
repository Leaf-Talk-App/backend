from pydantic import BaseModel, EmailStr

class RegisterSchema(BaseModel):
    name: str
    email: EmailStr
    password: str

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
