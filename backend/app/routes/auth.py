"""Authentication endpoints fail closed until secure OTP delivery/storage exists."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class SendOtpRequest(BaseModel):
    identity: str = Field(min_length=3, max_length=320)
    channel: str = Field(pattern="^(email|phone)$")


class VerifyOtpRequest(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=4, max_length=12)


@router.post("/otp/send")
def send_otp(_payload: SendOtpRequest):
    raise HTTPException(status_code=503, detail="OTP delivery is not configured. Authentication is unavailable.")


@router.post("/otp/verify")
def verify_otp(_payload: VerifyOtpRequest):
    raise HTTPException(status_code=503, detail="OTP verification is not configured. Authentication is unavailable.")
