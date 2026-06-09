import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def _build_message(to_email: str, subject: str, html: str) -> MIMEMultipart:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM or settings.EMAIL_USERNAME
    message["To"] = to_email
    message.attach(MIMEText(html, "html", "utf-8"))
    return message


def send_email(to_email: str, subject: str, html: str) -> None:
    """Envia via SMTP do Gmail. Tenta 587 (STARTTLS) e, se falhar, 465 (SSL).
    Loga o resultado/erro para diagnóstico nos logs do Render."""
    sender = settings.EMAIL_FROM or settings.EMAIL_USERNAME
    message = _build_message(to_email, subject, html)
    context = ssl.create_default_context()

    # 1) Porta 587 + STARTTLS (padrão do Gmail)
    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.sendmail(sender, [to_email], message.as_string())
        print(f"[EMAIL] enviado via 587 -> {to_email}")
        return
    except Exception as exc:
        print(f"[EMAIL] 587 falhou: {type(exc).__name__}: {exc}")

    # 2) Fallback porta 465 + SSL (caso 587 esteja bloqueada)
    try:
        with smtplib.SMTP_SSL(settings.EMAIL_HOST, 465, timeout=20, context=context) as server:
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.sendmail(sender, [to_email], message.as_string())
        print(f"[EMAIL] enviado via 465 -> {to_email}")
    except Exception as exc:
        print(f"[EMAIL] 465 falhou: {type(exc).__name__}: {exc}")
        raise
