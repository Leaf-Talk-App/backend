import resend
from app.core.config import settings
resend.api_key = settings.RESEND_API_KEY

def send_email(
    to_email: str,
    subject: str,
    html: str
):
    params = {
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    return resend.Emails.send(params)