"""Short-lived email/phone OTP login for the PR Mentor demo and configured deployments."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import smtplib
import threading
import time
from email.message import EmailMessage
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auth", tags=["auth"])
OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
SEND_COOLDOWN_SECONDS = 30
SEND_WINDOW_SECONDS = 900
SEND_MAX_PER_WINDOW = 3
_lock = threading.Lock()
_challenges: dict[str, dict] = {}
_send_history: dict[str, list[float]] = {}
_sessions: dict[str, dict] = {}


class SendOtpRequest(BaseModel):
    method: Literal["email", "phone"]
    identifier: str = Field(min_length=5, max_length=254)


class VerifyOtpRequest(BaseModel):
    challenge_id: str = Field(min_length=20, max_length=64)
    code: str = Field(pattern=r"^\d{6}$")


def _normalise(method: str, identifier: str) -> str:
    value = identifier.strip()
    if method == "email":
        value = value.lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise HTTPException(status_code=422, detail="Enter a valid email address.")
    else:
        value = re.sub(r"[\s()-]", "", value)
        if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
            raise HTTPException(status_code=422, detail="Use an international phone number, for example +14155550123.")
    return value


def _deliver_email(recipient: str, code: str) -> None:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        raise HTTPException(status_code=503, detail="Email OTP delivery is not configured. Set SMTP_HOST and SMTP_FROM.")
    message = EmailMessage()
    message["Subject"] = "Your PR Mentor sign-in code"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(f"Your PR Mentor sign-in code is {code}. It expires in 5 minutes. If you did not request it, ignore this email.")
    port = int(os.getenv("SMTP_PORT", "587"))
    username, password = os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD")
    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=502, detail="Could not deliver the email OTP. Check the SMTP settings.") from exc


def _deliver_sms(recipient: str, code: str) -> None:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    if not account_sid or not auth_token or not (service_sid or from_number):
        raise HTTPException(status_code=503, detail="SMS OTP delivery is not configured. Set Twilio credentials and a sender.")
    fields = {"To": recipient, "Body": f"Your PR Mentor sign-in code is {code}. It expires in 5 minutes."}
    fields["MessagingServiceSid" if service_sid else "From"] = service_sid or from_number or ""
    request = Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        data=urlencode(fields).encode(),
        headers={"Authorization": "Basic " + __import__("base64").b64encode(f"{account_sid}:{auth_token}".encode()).decode(), "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            if response.status >= 300:
                raise HTTPException(status_code=502, detail="Could not deliver the SMS OTP.")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="Could not deliver the SMS OTP. Check the Twilio settings.") from exc


@router.post("/otp/send")
def send_otp(payload: SendOtpRequest):
    identifier = _normalise(payload.method, payload.identifier)
    now = time.time()
    with _lock:
        history = [sent for sent in _send_history.get(identifier, []) if now - sent < SEND_WINDOW_SECONDS]
        if history and now - history[-1] < SEND_COOLDOWN_SECONDS:
            raise HTTPException(status_code=429, detail="Please wait before requesting another code.")
        if len(history) >= SEND_MAX_PER_WINDOW:
            raise HTTPException(status_code=429, detail="Too many codes requested. Try again in 15 minutes.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    delivery_mode = os.getenv("PR_MENTOR_OTP_MODE", "demo").lower()
    environment = os.getenv("PR_MENTOR_ENV", "development").lower()
    if delivery_mode == "demo":
        if environment in {"production", "prod"}:
            raise HTTPException(status_code=503, detail="Demo OTP delivery is disabled in production.")
    elif delivery_mode == "smtp" and payload.method == "email":
        _deliver_email(identifier, code)
    elif delivery_mode == "twilio" and payload.method == "phone":
        _deliver_sms(identifier, code)
    else:
        raise HTTPException(status_code=503, detail="No delivery provider is configured for this login method.")

    challenge_id = uuid4().hex
    salt = secrets.token_bytes(16)
    code_hash = hashlib.sha256(salt + code.encode()).hexdigest()
    with _lock:
        history = [sent for sent in _send_history.get(identifier, []) if now - sent < SEND_WINDOW_SECONDS]
        history.append(now)
        _send_history[identifier] = history
        _challenges[challenge_id] = {
            "identifier": identifier, "method": payload.method, "salt": salt,
            "code_hash": code_hash, "expires": now + OTP_TTL_SECONDS, "attempts": 0,
        }
    result = {"challenge_id": challenge_id, "expires_in": OTP_TTL_SECONDS, "delivery": "demo" if delivery_mode == "demo" else ("email" if payload.method == "email" else "sms")}
    if delivery_mode == "demo":
        result["demo_otp"] = code
    return result


@router.post("/otp/verify")
def verify_otp(payload: VerifyOtpRequest):
    now = time.time()
    with _lock:
        challenge = _challenges.get(payload.challenge_id)
        if not challenge or challenge["expires"] <= now:
            _challenges.pop(payload.challenge_id, None)
            raise HTTPException(status_code=400, detail="This code has expired. Request a new one.")
        challenge["attempts"] += 1
        candidate = hashlib.sha256(challenge["salt"] + payload.code.encode()).hexdigest()
        valid = hmac.compare_digest(candidate, challenge["code_hash"])
        if not valid:
            if challenge["attempts"] >= OTP_MAX_ATTEMPTS:
                _challenges.pop(payload.challenge_id, None)
                raise HTTPException(status_code=429, detail="Too many incorrect attempts. Request a new code.")
            raise HTTPException(status_code=400, detail="That code does not match. Check it and try again.")
        _challenges.pop(payload.challenge_id, None)
        token = secrets.token_urlsafe(32)
        _sessions[token] = {"identity": challenge["identifier"], "created": now}
        return {"access_token": token, "token_type": "bearer", "identity": challenge["identifier"]}
