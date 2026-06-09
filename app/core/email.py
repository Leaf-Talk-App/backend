import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def send_email(to: str, subject: str, html: str):
    """Envia e-mail via Gmail SMTP (porta 587 + STARTTLS)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_USER
        msg["To"] = to
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.EMAIL_HOST, int(settings.EMAIL_PORT)) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_USER, to, msg.as_string())
            print(f"[EMAIL] Gmail ok -> {to}")
    except Exception as e:
        print(f"[EMAIL] ERRO: {e}")
        raise
