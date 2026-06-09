import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from app.core.config import settings


def _send_via_brevo(to: str, subject: str, html: str) -> bool:
    """Envia via API HTTP do Brevo. Funciona no Render (HTTPS), onde o SMTP de
    saída é bloqueado. Grátis 300/dia, entrega para qualquer e-mail com só um
    sender verificado (sem domínio próprio). Retorna True se aceito."""
    resp = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": settings.BREVO_API_KEY,
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={
            "sender": {"email": settings.BREVO_FROM_EMAIL, "name": settings.BREVO_FROM_NAME},
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": html,
        },
        timeout=15,
    )
    if resp.status_code >= 400:
        print(f"[EMAIL] ERRO: Brevo {resp.status_code}: {resp.text}")
        return False
    print(f"[EMAIL] Brevo ok -> {to}")
    return True


def _send_via_smtp(to: str, subject: str, html: str) -> None:
    """Fallback SMTP (uso local/dev — no Render a porta é bloqueada)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_USER
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(settings.EMAIL_HOST, int(settings.EMAIL_PORT), timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        server.sendmail(settings.EMAIL_USER, to, msg.as_string())
    print(f"[EMAIL] Gmail ok -> {to}")


def send_email(to: str, subject: str, html: str):
    """Brevo (HTTP) se houver key; senão SMTP (local). Loga sucesso/erro."""
    try:
        if settings.BREVO_API_KEY:
            _send_via_brevo(to, subject, html)
            return
        _send_via_smtp(to, subject, html)
    except Exception as e:
        print(f"[EMAIL] ERRO: {type(e).__name__}: {e}")
        raise
