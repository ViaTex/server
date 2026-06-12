"""
Comprehensive SMTP Diagnostic & Test Script for DishaSetu
==========================================================

Usage (run from the server/ directory):
  ..\\.venv\\Scripts\\python.exe scripts\\test_smtp.py [recipient_email]

  If recipient_email is omitted the test sends to MAIL_USERNAME (self-test).

What this script does:
  1. Validates all MAIL_* environment variables.
  2. Prints a redacted config summary.
  3. Attempts a raw TCP connection to smtp.gmail.com:587.
  4. Performs a full SMTP handshake with STARTTLS + App Password login.
  5. Sends a test email if all previous steps pass.
  6. Reports exactly which step failed and how to fix it.

Common 535 Fix
--------------
  ✗ You are using your normal Gmail password    → will always get 535
  ✓ You must use a Gmail App Password (16 chars)
    Steps:
      1. Enable 2-Step Verification: https://myaccount.google.com/security
      2. Generate App Password:      https://myaccount.google.com/apppasswords
         → Select "Mail" + "Other (custom name: DishaSetu)"
         → Copy the 16-character code (spaces are auto-stripped)
      3. Paste the 16-char code as MAIL_PASSWORD in server/.env
      4. Set MAIL_USERNAME to the Gmail address that owns the App Password
"""

from __future__ import annotations

import smtplib
import socket
import ssl
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Path setup — allow running from server/ or from project root
# ---------------------------------------------------------------------------
SERVER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_DIR))

# Load .env early so pydantic-settings picks it up
try:
    from dotenv import load_dotenv
    load_dotenv(SERVER_DIR / ".env", override=True)
except ImportError:
    pass  # dotenv is optional; settings will still load from os.environ

from app.core.config import settings  # noqa: E402 (after sys.path insert)


# ---------------------------------------------------------------------------
# ANSI colours (disabled on Windows if not supported)
# ---------------------------------------------------------------------------
def _supports_colour() -> bool:
    return sys.stdout.isatty() and os.name != "nt" or "WT_SESSION" in os.environ

_C = _supports_colour()
OK    = "\033[92m✓\033[0m" if _C else "[OK]"
FAIL  = "\033[91m✗\033[0m" if _C else "[FAIL]"
INFO  = "\033[94m•\033[0m" if _C else "[INFO]"
WARN  = "\033[93m!\033[0m" if _C else "[WARN]"
BOLD  = "\033[1m"          if _C else ""
RESET = "\033[0m"          if _C else ""

GMAIL_HOST = "smtp.gmail.com"
GMAIL_PORT = 587


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

def step(label: str) -> None:
    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}{label}{RESET}")
    print(f"{'─' * 60}")


def ok(msg: str) -> None:
    print(f"  {OK}  {msg}")


def fail(msg: str) -> None:
    print(f"  {FAIL}  {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"  {INFO}  {msg}")


def warn(msg: str) -> None:
    print(f"  {WARN}  {msg}")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_env_vars() -> tuple[str, str]:
    """Validate and print all MAIL_* settings. Returns (username, password)."""
    step("STEP 1 — Environment Variable Validation")

    username = (settings.MAIL_USERNAME or "").strip()
    password = (settings.MAIL_PASSWORD or "").strip()
    # Gmail strips spaces from App Passwords
    password_clean = password.replace(" ", "")
    from_addr = (settings.MAIL_FROM_ADDRESS or "").strip()
    host = (settings.MAIL_HOST or "").strip()
    port = settings.MAIL_PORT
    encryption = (settings.MAIL_ENCRYPTION or "tls").strip().lower()

    # Print redacted summary
    info(f"MAIL_HOST        = {host or '(not set)'}")
    info(f"MAIL_PORT        = {port}")
    info(f"MAIL_ENCRYPTION  = {encryption}")
    info(f"MAIL_USERNAME    = {username or '(not set)'}")
    info(f"MAIL_PASSWORD    = {'*' * len(password_clean) if password_clean else '(not set)'} ({len(password_clean)} chars)")
    info(f"MAIL_FROM_ADDRESS= {from_addr or '(not set)'}")
    info(f"MAIL_FROM_NAME   = {settings.MAIL_FROM_NAME or '(not set)'}")
    info(f"MAIL_DEBUG       = {settings.MAIL_DEBUG}")
    info(f"MAIL_RETRY_COUNT = {settings.MAIL_RETRY_COUNT}")

    errors: list[str] = []

    if not host:
        errors.append("MAIL_HOST is empty → set MAIL_HOST=smtp.gmail.com")
    elif host != GMAIL_HOST:
        warn(f"MAIL_HOST={host!r} is not smtp.gmail.com — continuing anyway")

    if not port:
        errors.append("MAIL_PORT is 0 → set MAIL_PORT=587")

    PLACEHOLDERS = {"yourgmail@gmail.com", "your_gmail_address@gmail.com", "your-email@example.com", ""}
    if not username:
        errors.append("MAIL_USERNAME is empty → set your Gmail address")
    elif username.lower() in PLACEHOLDERS or username.lower().startswith("your"):
        errors.append(
            f"MAIL_USERNAME={username!r} looks like a placeholder.\n"
            "     Edit server/.env and set MAIL_USERNAME=your.actual@gmail.com"
        )

    if not password:
        errors.append("MAIL_PASSWORD is empty → paste your 16-char Gmail App Password")
    elif len(password_clean) < 16:
        errors.append(
            f"MAIL_PASSWORD has only {len(password_clean)} chars (expected 16).\n"
            "     Verify you copied the full App Password from "
            "https://myaccount.google.com/apppasswords"
        )
    elif password_clean.lower() in {"your_16_char_google_app_password", "xxxxxxxxxxxxxxxx"}:
        errors.append(
            "MAIL_PASSWORD is still a placeholder.\n"
            "     Generate a real App Password at https://myaccount.google.com/apppasswords"
        )
    elif len(password_clean) > 16:
        warn(
            f"MAIL_PASSWORD has {len(password_clean)} chars (expected 16). "
            "Make sure you didn't paste extra characters."
        )

    if not from_addr:
        errors.append("MAIL_FROM_ADDRESS is empty → usually same as MAIL_USERNAME for Gmail")

    if errors:
        print()
        fail("Environment validation FAILED:")
        for e in errors:
            fail(f"  {e}")
        sys.exit(1)

    ok("All required MAIL_* variables are set and look valid.")
    return username, password_clean


def check_tcp_connectivity(host: str, port: int) -> None:
    """Verify we can open a TCP socket to the SMTP server."""
    step(f"STEP 2 — TCP Connectivity to {host}:{port}")
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            ok(f"TCP connection to {host}:{port} succeeded.")
            info(f"  Local address : {sock.getsockname()}")
            info(f"  Remote address: {sock.getpeername()}")
    except socket.timeout:
        fail(f"Connection to {host}:{port} timed out after 10 seconds.")
        fail("  Possible causes: firewall blocking port 587, or proxy intercepting traffic.")
        sys.exit(1)
    except OSError as exc:
        fail(f"Cannot connect to {host}:{port}: {exc}")
        fail("  Check your internet connection and any corporate firewall/proxy settings.")
        sys.exit(1)


def check_smtp_starttls(host: str, port: int, username: str, password: str) -> None:
    """Perform a full SMTP handshake: EHLO → STARTTLS → EHLO → AUTH → QUIT."""
    step(f"STEP 3 — SMTP STARTTLS Handshake & Authentication ({host}:{port})")
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.set_debuglevel(1)  # Always show the SMTP transcript for this diagnostic

            # Initial EHLO
            code, resp = server.ehlo()
            info(f"EHLO response: {code} {resp.decode(errors='replace')[:80]}")
            if code != 250:
                fail(f"Unexpected EHLO response code {code}; expected 250.")
                sys.exit(1)

            # STARTTLS
            if not server.has_extn("STARTTLS"):
                warn("Server did not advertise STARTTLS — attempting anyway.")
            server.starttls(context=ctx)
            ok("STARTTLS negotiated successfully.")

            # Re-EHLO after STARTTLS
            code, resp = server.ehlo()
            info(f"Post-STARTTLS EHLO: {code} {resp.decode(errors='replace')[:80]}")

            # AUTH
            try:
                server.login(username, password)
                ok(f"SMTP authentication succeeded for {username}.")
            except smtplib.SMTPAuthenticationError as auth_exc:
                fail(f"SMTP 535 Authentication Failed: {auth_exc}")
                fail("")
                fail("  This means your password was rejected by Gmail.")
                fail("  Diagnosis:")
                fail("    • Are you using your normal Gmail password? → Replace with an App Password.")
                fail("    • Is 2-Step Verification enabled?           → Required for App Passwords.")
                fail("    • Is the App Password only 16 chars?        → Check for extra chars.")
                fail("    • Is MAIL_USERNAME the Gmail that owns the App Password?")
                fail("")
                fail("  Fix:")
                fail("    1. https://myaccount.google.com/security — enable 2-Step Verification")
                fail("    2. https://myaccount.google.com/apppasswords — generate App Password")
                fail("    3. Paste the 16-char code as MAIL_PASSWORD in server/.env")
                sys.exit(1)

    except smtplib.SMTPConnectError as exc:
        fail(f"SMTP connection error: {exc}")
        sys.exit(1)
    except ssl.SSLError as exc:
        fail(f"TLS/SSL error during STARTTLS: {exc}")
        fail("  Try setting MAIL_ENCRYPTION=ssl and MAIL_PORT=465 as an alternative.")
        sys.exit(1)


def send_test_email(recipient: str) -> None:
    """Send a formatted test email using the production send_email utility."""
    from app.core.mail import send_email, MailAuthError, MailConfigError, MailSendError

    step(f"STEP 4 — Sending Test Email to {recipient}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"DishaSetu SMTP Test — {now}"
    body = (
        f"This is an automated SMTP test from DishaSetu.\n\n"
        f"  Sent at  : {now}\n"
        f"  From     : {settings.MAIL_FROM_ADDRESS}\n"
        f"  To       : {recipient}\n"
        f"  Host     : {settings.MAIL_HOST}:{settings.MAIL_PORT}\n"
        f"  TLS mode : {settings.MAIL_ENCRYPTION}\n\n"
        "If you received this, your Gmail SMTP + App Password setup is working correctly!"
    )
    html_body = f"""
<html>
<body style="font-family:Arial,sans-serif;background:#f0f4ff;padding:24px;">
  <div style="max-width:580px;margin:0 auto;background:#fff;border-radius:12px;padding:28px;border:1px solid #d6e4ff;">
    <h2 style="color:#163b82;margin:0 0 8px;">✅ DishaSetu SMTP Test</h2>
    <p style="color:#3f4f6b;">Your Gmail SMTP + App Password configuration is working correctly.</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;color:#374151;">
      <tr><td style="padding:6px 0;color:#6b7280;">Sent at</td><td style="padding:6px 0;font-weight:600;">{now}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;">From</td><td style="padding:6px 0;font-weight:600;">{settings.MAIL_FROM_ADDRESS}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;">To</td><td style="padding:6px 0;font-weight:600;">{recipient}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;">SMTP Host</td><td style="padding:6px 0;font-weight:600;">{settings.MAIL_HOST}:{settings.MAIL_PORT}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;">TLS Mode</td><td style="padding:6px 0;font-weight:600;">{settings.MAIL_ENCRYPTION.upper()}</td></tr>
    </table>
    <p style="font-size:12px;color:#9ca3af;">DishaSetu automated SMTP diagnostic</p>
  </div>
</body>
</html>
"""
    try:
        send_email(to_email=recipient, subject=subject, body=body, html_body=html_body)
        ok(f"Test email successfully delivered to {recipient}.")
        ok("Your SMTP configuration is production-ready! 🎉")
    except MailConfigError as exc:
        fail(f"Config error: {exc}")
        sys.exit(1)
    except MailAuthError as exc:
        fail(f"Auth error: {exc}")
        sys.exit(1)
    except MailSendError as exc:
        fail(f"Send error: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  DishaSetu SMTP Diagnostic Tool{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    recipient = sys.argv[1].strip() if len(sys.argv) > 1 else settings.MAIL_USERNAME.strip()

    if not recipient:
        print("\nUsage: python scripts/test_smtp.py [recipient@example.com]")
        print("If recipient is omitted, sends to MAIL_USERNAME (self-test).")
        return 1

    info(f"Recipient: {recipient}")

    # Step 1 — validate env
    username, password = check_env_vars()

    # Step 2 — TCP connectivity
    check_tcp_connectivity(GMAIL_HOST, GMAIL_PORT)

    # Step 3 — SMTP auth (raw, so we see the exact SMTP transcript)
    check_smtp_starttls(GMAIL_HOST, GMAIL_PORT, username, password)

    # Step 4 — end-to-end test via production utility
    send_test_email(recipient)

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{OK}  All checks passed. SMTP is configured correctly.")
    print(f"{BOLD}{'=' * 60}{RESET}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
