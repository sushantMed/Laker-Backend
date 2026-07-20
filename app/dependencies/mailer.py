# app/api/deps.py

from app.core.config import settings
from app.core.mailer import Mailer


def get_mailer() -> Mailer:
    return Mailer(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        from_email=settings.smtp_from_email,
        from_name=settings.smtp_from_name,
        use_tls=settings.smtp_use_tls,
        use_ssl=False,  # Assuming SSL is not used; adjust as needed
    )
