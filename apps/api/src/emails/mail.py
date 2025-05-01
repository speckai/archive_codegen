import urllib.parse

import resend
from src.config import RESEND_API_KEY
from src.utils.logging import logger

resend.api_key = RESEND_API_KEY

DOMAIN: str = "mail.speck.sh"


def read_email() -> str:
    with open("src/emails/email.html", "r") as f:
        return f.read()


WAITLIST_EMAIL: str = read_email()


def send_email(
    to: str,
    subject: str,
    body: str,
    from_name: str = "Speck",
    from_email: str = "speck",
) -> resend.Email:
    params: resend.Emails.SendParams = {
        "from": f"{from_name} <{from_email}@{DOMAIN}>",
        "to": to,
        "reply_to": "founders@speck.sh",
        "subject": subject,
        "html": body,
    }

    email: resend.Email = resend.Emails.send(params)
    return email


def send_waitlist_email(to_email: str, first_name: str) -> bool:
    confirm_url: str = f"https://speck.sh/waitlist?email={urllib.parse.quote(to_email)}"
    html: str = WAITLIST_EMAIL.replace("{CONFIRM_URL}", confirm_url)
    html = html.replace("{NAME}", first_name)
    send_email(to_email, "Confirm Your Speck Waitlist", html)
    return True


if __name__ == "__main__":
    test_html = WAITLIST_EMAIL.replace("{CONFIRM_URL}", "https://speck.sh/waitlist")
    res = send_waitlist_email("raghav@speck.sh", "Raghav")
    logger.info(res)
