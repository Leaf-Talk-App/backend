import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from app.core.config import settings


def _send_via_mailersend(to_email: str, subject: str, html: str) -> bool:
    """Envia via API HTTP do MailerSend. Funciona no Render free (HTTPS), onde o
    SMTP de saída é bloqueado. No trial entrega para qualquer e-mail. True se aceito."""
    resp = httpx.post(
        "https://api.mailersend.com/v1/email",
        headers={
            "Authorization": f"Bearer {settings.MAILERSEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": {
                "email": settings.MAILERSEND_FROM_EMAIL,
                "name": settings.MAILERSEND_FROM_NAME,
            },
            "to": [{"email": to_email}],
            "subject": subject,
            "html": html,
        },
        timeout=15,
    )
    # MailerSend retorna 202 (Accepted) no sucesso
    if resp.status_code >= 400:
        print(f"[EMAIL] ERRO: MailerSend {resp.status_code}: {resp.text}")
        return False
    print(f"[EMAIL] MailerSend ok -> {to_email}")
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
    """MailerSend (HTTP) se houver key; senão SMTP. Loga sucesso/erro p/ diagnóstico."""
    try:
        if settings.MAILERSEND_API_KEY:
            if _send_via_mailersend(to_email, subject, html):
                return
            if settings.EMAIL_USERNAME and settings.EMAIL_PASSWORD:
                _send_via_smtp(to_email, subject, html)
            return
        _send_via_smtp(to_email, subject, html)
    except Exception as e:
        print(f"[EMAIL] ERRO: {type(e).__name__}: {e}")
        raise
