import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from app.core.config import settings


def _send_via_resend(to_email: str, subject: str, html: str) -> bool:
    """Envia via API HTTP do Resend. Funciona no Render free (HTTPS), onde o
    SMTP de saída é bloqueado. Retorna True se aceito."""
    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
        json={
            "from": settings.RESEND_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html,
        },
        timeout=15,
    )
    if resp.status_code >= 400:
        print(f"[EMAIL] Resend falhou {resp.status_code}: {resp.text}")
        return False
    print(f"[EMAIL] Resend ok -> {to_email}")
    return True


def _send_via_smtp(to_email: str, subject: str, html: str) -> None:
    """Fallback SMTP (uso local/dev — no Render free a porta é bloqueada)."""
    sender = settings.EMAIL_FROM or settings.EMAIL_USERNAME
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=15) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
        server.sendmail(sender, [to_email], message.as_string())
    print(f"[EMAIL] SMTP ok -> {to_email}")


def send_email(to_email: str, subject: str, html: str) -> None:
    """Resend (HTTP) se houver key; senão SMTP. Loga o resultado p/ diagnóstico."""
    try:
        if settings.RESEND_API_KEY:
            if _send_via_resend(to_email, subject, html):
                return
            # Resend falhou — tenta SMTP só se houver credenciais (local)
            if settings.EMAIL_USERNAME and settings.EMAIL_PASSWORD:
                _send_via_smtp(to_email, subject, html)
            return
        _send_via_smtp(to_email, subject, html)
    except Exception as exc:
        print(f"[EMAIL] envio falhou para {to_email}: {type(exc).__name__}: {exc}")
        raise
