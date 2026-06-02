"""
mail.py — Production-level Gmail SMTP email utility for DishaSetu.

Authentication: Gmail App Password (16-char, generated at https://myaccount.google.com/apppasswords)
Protocol:       SMTP with STARTTLS on port 587  (or SMTP_SSL on port 465)
Debug:          Set MAIL_DEBUG=true in .env to print the full SMTP handshake to stdout.

Common 535 Fix Checklist
--------------------------
1. Enable 2-Step Verification on the Gmail account.
2. Generate an App Password at https://myaccount.google.com/apppasswords
   (select "Mail" → "Other (custom name)").
3. Paste the 16-char App Password into MAIL_PASSWORD in .env.
   Spaces in the password are automatically stripped — copy as-is.
4. Set MAIL_USERNAME to the *same* Gmail address that owns the App Password.
5. Confirm that MAIL_HOST=smtp.gmail.com and MAIL_PORT=587.
6. Do NOT use your normal Gmail login password here — it will always fail with 535.
"""

import smtplib
import ssl
import time
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Optional
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class MailConfigError(Exception):
    """Raised when required mail environment variables are missing or contain placeholders."""


class MailAuthError(Exception):
    """Raised when SMTP login fails (535 Authentication Failed)."""


class MailSendError(Exception):
    """Raised when the message could not be delivered after all retries."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_KNOWN_PLACEHOLDERS = {
    "",
    "yourgmail@gmail.com",
    "your_16_char_google_app_password",
    "xxxx xxxx xxxx xxxx",        # our own template placeholder
    "emailapikey",
    "your-email@example.com",
    "your_gmail_address@gmail.com",
}


def _is_placeholder(value: str) -> bool:
    """Return True if the value looks like an unfilled template placeholder."""
    stripped = value.strip().lower()
    if stripped in _KNOWN_PLACEHOLDERS:
        return True
    # Generic "your_*" / "your-*" patterns
    if stripped.startswith(("your_", "your-", "<", "enter_", "replace_")):
        return True
    return False


def _validate_mail_config() -> None:
    """Raise MailConfigError with actionable messages if the mail env is not ready."""
    errors: list[str] = []

    host = (settings.MAIL_HOST or "").strip()
    port = settings.MAIL_PORT
    username = (settings.MAIL_USERNAME or "").strip()
    password = (settings.MAIL_PASSWORD or "").strip()
    from_addr = (settings.MAIL_FROM_ADDRESS or "").strip()

    if not host:
        errors.append("MAIL_HOST is not set.")
    if not port:
        errors.append("MAIL_PORT is not set.")
    if not username:
        errors.append("MAIL_USERNAME is not set.")
    elif _is_placeholder(username):
        errors.append(
            f"MAIL_USERNAME looks like a placeholder ({username!r}). "
            "Set it to your actual Gmail address."
        )
    if not password:
        errors.append("MAIL_PASSWORD is not set.")
    elif _is_placeholder(password):
        errors.append(
            "MAIL_PASSWORD looks like a placeholder. "
            "Generate a Gmail App Password at https://myaccount.google.com/apppasswords "
            "and paste the 16-char code here."
        )
    if not from_addr:
        errors.append("MAIL_FROM_ADDRESS is not set.")
    elif _is_placeholder(from_addr):
        errors.append(
            f"MAIL_FROM_ADDRESS looks like a placeholder ({from_addr!r}). "
            "Set it to your actual Gmail address."
        )

    if errors:
        msg = "Email is not configured correctly:\n" + "\n".join(f"  • {e}" for e in errors)
        logger.error("Mail config validation failed", errors=errors)
        raise MailConfigError(msg)

    logger.debug(
        "Mail config validated",
        host=host,
        port=port,
        encryption=settings.MAIL_ENCRYPTION,
        username=username,
        from_address=from_addr,
        debug_mode=settings.MAIL_DEBUG,
    )


# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------

def send_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> None:
    """
    Send an email via Gmail SMTP.

    Args:
        to_email:  Recipient address.
        subject:   Email subject line.
        body:      Plain-text body (always included for RFC compliance).
        html_body: Optional HTML alternative body.

    Raises:
        MailConfigError:  env variables are missing or still placeholder values.
        MailAuthError:    SMTP 535 — wrong password / App Password not set up.
        MailSendError:    Network error or recipient rejected after all retries.
    """
    _validate_mail_config()

    recipient = to_email.strip().lower()
    if "@" not in recipient:
        raise MailSendError(f"Invalid recipient email address: {recipient!r}")

    # Build the message
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_ADDRESS}>"
    message["To"] = recipient
    message["Message-ID"] = make_msgid(domain=settings.MAIL_FROM_ADDRESS.split("@")[-1])
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    # Normalize credentials
    host = settings.MAIL_HOST.strip()
    port = settings.MAIL_PORT
    username = settings.MAIL_USERNAME.strip()
    # Gmail App Passwords are 16 chars; users often copy them with spaces → strip all spaces
    password = settings.MAIL_PASSWORD.strip()
    if host.lower() == "smtp.gmail.com":
        password = password.replace(" ", "")

    encryption = (settings.MAIL_ENCRYPTION or "tls").strip().lower()
    debug_level = 2 if settings.MAIL_DEBUG else 0  # 2 = verbose SMTP transcript

    logger.info(
        "SMTP: preparing to send",
        host=host,
        port=port,
        encryption=encryption,
        username=username,
        password_length=len(password),
        to=recipient,
        subject=subject,
        debug_mode=settings.MAIL_DEBUG,
    )

    last_exc: Optional[Exception] = None
    max_attempts = max(1, settings.MAIL_RETRY_COUNT)

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info("SMTP: connecting", attempt=attempt, host=host, port=port)
            _do_send(
                host=host,
                port=port,
                username=username,
                password=password,
                encryption=encryption,
                message=message,
                debug_level=debug_level,
                attempt=attempt,
            )
            logger.info("SMTP: message delivered", attempt=attempt, to=recipient)
            return  # ✓ success

        except smtplib.SMTPAuthenticationError as exc:
            # Do NOT retry auth failures — the App Password won't become valid on retry.
            code, detail = exc.smtp_code, exc.smtp_error
            logger.error(
                "SMTP: 535 authentication failed — check your App Password",
                smtp_code=code,
                smtp_detail=detail.decode(errors="replace") if isinstance(detail, bytes) else str(detail),
                host=host,
                username=username,
                hint=(
                    "Gmail requires an App Password (not your normal Gmail password). "
                    "Generate one at https://myaccount.google.com/apppasswords"
                ),
            )
            raise MailAuthError(
                f"SMTP authentication failed ({code}). "
                "Gmail requires an App Password, not your normal password. "
                "Generate one at https://myaccount.google.com/apppasswords"
            ) from exc

        except smtplib.SMTPRecipientsRefused as exc:
            logger.error("SMTP: recipient refused", recipient=recipient, error=str(exc))
            raise MailSendError(f"Recipient {recipient!r} was refused by Gmail: {exc}") from exc

        except smtplib.SMTPException as exc:
            last_exc = exc
            logger.warning(
                "SMTP: send attempt failed",
                attempt=attempt,
                max_attempts=max_attempts,
                error=str(exc),
                error_type=type(exc).__name__,
            )

        except OSError as exc:
            last_exc = exc
            logger.warning(
                "SMTP: network error",
                attempt=attempt,
                max_attempts=max_attempts,
                error=str(exc),
            )

        # Retry delay (skip on the last attempt)
        if attempt < max_attempts:
            delay = max(1, settings.MAIL_RETRY_DELAY_SECONDS)
            logger.info("SMTP: retrying", delay_seconds=delay, next_attempt=attempt + 1)
            time.sleep(delay)

    raise MailSendError(
        f"Email delivery failed after {max_attempts} attempt(s): {last_exc}"
    )


def _do_send(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    encryption: str,
    message: EmailMessage,
    debug_level: int,
    attempt: int,
) -> None:
    """
    Perform the actual SMTP connection, authentication, and message delivery.

    Supports three TLS modes:
      - ``tls``  → SMTP on port 587 with STARTTLS upgrade (recommended for Gmail)
      - ``ssl``  → SMTP_SSL on port 465 (direct TLS)
      - ``none`` → plain SMTP (development only; not suitable for Gmail)
    """
    ssl_context = ssl.create_default_context()

    if encryption == "ssl":
        # Port 465 — wrap the connection in TLS from the start
        with smtplib.SMTP_SSL(host, port, context=ssl_context, timeout=30) as server:
            server.set_debuglevel(debug_level)
            logger.debug("SMTP_SSL: connected", attempt=attempt)
            server.login(username, password)
            logger.debug("SMTP_SSL: authenticated", attempt=attempt)
            refused = server.send_message(message)
            if refused:
                logger.warning("SMTP_SSL: some recipients refused", refused=refused)

    else:
        # Port 587 (or plain) — plain connection then STARTTLS upgrade
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.set_debuglevel(debug_level)
            # Initial EHLO to learn server capabilities
            code, response = server.ehlo()
            logger.debug(
                "SMTP EHLO",
                code=code,
                response=response.decode(errors="replace") if isinstance(response, bytes) else str(response),
                attempt=attempt,
            )

            if encryption == "tls":
                if not server.has_extn("STARTTLS"):
                    logger.warning(
                        "SMTP: STARTTLS not advertised by server — attempting anyway",
                        host=host,
                    )
                server.starttls(context=ssl_context)
                # Re-EHLO after STARTTLS so the server updates its capability list
                code, response = server.ehlo()
                logger.debug(
                    "SMTP EHLO after STARTTLS",
                    code=code,
                    response=response.decode(errors="replace") if isinstance(response, bytes) else str(response),
                    attempt=attempt,
                )

            logger.debug("SMTP: logging in", username=username, attempt=attempt)
            server.login(username, password)
            logger.debug("SMTP: authenticated successfully", attempt=attempt)

            refused = server.send_message(message)
            if refused:
                logger.warning("SMTP: some recipients refused", refused=refused)
