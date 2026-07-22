# app/core/mailer.py

from email.message import EmailMessage

import aiosmtplib


class Mailer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        from_name: str,
        use_tls: bool,
        use_ssl: bool,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.from_name = from_name
        self.use_tls = use_tls
        self.use_ssl = use_ssl

    async def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        html: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> None:
        message = EmailMessage()

        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = ", ".join(to)
        message["Subject"] = subject

        if cc:
            message["Cc"] = ", ".join(cc)

        message.set_content("Please use an HTML-compatible email client.")
        message.add_alternative(html, subtype="html")

        recipients = to + (cc or []) + (bcc or [])

        print(f"SMTP host = {self.host}")
        print("SMTP port = %s", self.port)

        await aiosmtplib.send(
            message,
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            use_tls=self.use_ssl,
            start_tls=self.use_tls,
            recipients=recipients,
        )
