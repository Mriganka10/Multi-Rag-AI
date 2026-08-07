import hashlib
import re
import secrets
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.core.audit import safe_tenant_id
from app.core.config import settings


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LOCAL_OTPS: dict[str, dict[str, Any]] = {}
_LOCAL_SESSIONS: dict[str, "CurrentUser"] = {}
_LOCAL_EMAIL_VERIFICATIONS: dict[str, dict[str, Any]] = {}


@dataclass(frozen=True)
class CurrentUser:
    email: str
    role: str
    tenant_id: str

    @property
    def username(self) -> str:
        return self.email


class OTPRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not EMAIL_PATTERN.match(email):
            raise ValueError("Enter a valid email address.")
        return email


class OTPVerifyRequest(OTPRequest):
    otp: str = Field(..., min_length=4, max_length=12)

    @field_validator("otp")
    @classmethod
    def normalize_otp(cls, value: str) -> str:
        otp = value.strip().replace(" ", "")
        if not otp.isdigit():
            raise ValueError("OTP must contain digits only.")
        return otp


class AuthService:
    def request_signup_verification(self, email: str) -> dict[str, Any]:
        normalized_email = OTPRequest(email=email).email
        current_status = self._email_verification_status(normalized_email)
        if current_status == "SUCCESS":
            self._ensure_user(normalized_email)
            return {
                "status": "verified",
                "email": normalized_email,
                "message": "Email is already verified. You can return to login and request an OTP.",
            }

        provider = settings.email_provider.lower()
        if provider != "ses":
            self._save_email_verification(
                normalized_email,
                "SUCCESS",
                provider=provider,
                detail="Non-SES provider; email verification marked complete.",
            )
            self._ensure_user(normalized_email)
            return {
                "status": "verified",
                "email": normalized_email,
                "message": "Email is verified. You can return to login and request an OTP.",
            }

        try:
            self._ses_client().create_email_identity(EmailIdentity=normalized_email)
            self._save_email_verification(
                normalized_email,
                "PENDING",
                provider="ses",
                detail="AWS SES verification email requested.",
            )
        except Exception as exc:
            status = self._email_verification_status(normalized_email)
            if status == "SUCCESS":
                self._ensure_user(normalized_email)
                return {
                    "status": "verified",
                    "email": normalized_email,
                    "message": "Email is already verified. You can return to login and request an OTP.",
                }
            if status in {"PENDING", "TEMPORARY_FAILURE"}:
                return {
                    "status": "pending",
                    "email": normalized_email,
                    "message": (
                        "Verification email was already requested. Open the AWS email and click "
                        "the verification link, then return to login and request OTP."
                    ),
                }
            self._save_email_verification(
                normalized_email,
                status or "UNKNOWN",
                provider="ses",
                detail=f"SES verification request failed: {exc}",
            )
            raise HTTPException(
                status_code=503,
                detail="Unable to start email verification. Please try again later.",
            ) from exc

        return {
            "status": "pending",
            "email": normalized_email,
            "message": (
                "Verification email sent. Open that email and click the AWS verification link, "
                "then return here and request OTP."
            ),
        }

    def request_otp(self, email: str) -> dict[str, Any]:
        normalized_email = OTPRequest(email=email).email
        if self._verification_required() and not self._email_verified(normalized_email):
            raise HTTPException(
                status_code=403,
                detail=(
                    "This email is not verified yet. Open /register, complete the email "
                    "verification link, then request OTP."
                ),
            )
        otp = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.otp_ttl_minutes)
        self._store_otp(normalized_email, otp, expires_at)
        self._send_otp_email(normalized_email, otp)

        response: dict[str, Any] = {
            "message": "OTP sent to the registered email address.",
            "email": normalized_email,
            "expires_in_minutes": settings.otp_ttl_minutes,
        }
        if settings.otp_dev_mode or settings.environment.lower() != "production":
            response["dev_otp"] = otp
        return response

    def verify_otp(self, email: str, otp: str) -> tuple[CurrentUser, str]:
        payload = OTPVerifyRequest(email=email, otp=otp)
        if not self._verify_otp(payload.email, payload.otp):
            raise HTTPException(status_code=401, detail="Invalid or expired OTP.")

        user = self._ensure_user(payload.email)
        session_token = secrets.token_urlsafe(40)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.auth_session_ttl_minutes)
        self._store_session(session_token, user, expires_at)
        return user, session_token

    def current_user(self, request: Request) -> CurrentUser:
        if not settings.auth_enabled:
            return CurrentUser(email="local-dev@local", role="admin", tenant_id="local-dev")

        token = request.cookies.get(settings.auth_session_cookie_name)
        if not token:
            raise HTTPException(status_code=401, detail="Sign in required.")

        user = self._get_session(token)
        if user is None:
            raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
        return user

    def logout(self, request: Request) -> None:
        token = request.cookies.get(settings.auth_session_cookie_name)
        if token:
            self._delete_session(token)

    def _store_otp(self, email: str, otp: str, expires_at: datetime) -> None:
        otp_hash = self._hash_secret(otp)
        if settings.database_url:
            self._with_db(
                """
                insert into auth_otp_challenges (email, otp_hash, expires_at, consumed_at, created_at)
                values (%s, %s, %s, null, now())
                """,
                (email, otp_hash, expires_at),
            )
            return

        _LOCAL_OTPS[email] = {"otp_hash": otp_hash, "expires_at": expires_at, "consumed": False}

    def _verify_otp(self, email: str, otp: str) -> bool:
        otp_hash = self._hash_secret(otp)
        now = datetime.now(UTC)
        if settings.database_url:
            rows = self._fetch_db(
                """
                select id, otp_hash
                from auth_otp_challenges
                where email = %s
                  and consumed_at is null
                  and expires_at > now()
                order by id desc
                limit 1
                """,
                (email,),
            )
            if not rows:
                return False
            challenge_id, stored_hash = rows[0]
            if not secrets.compare_digest(stored_hash, otp_hash):
                return False
            self._with_db(
                "update auth_otp_challenges set consumed_at = now() where id = %s",
                (challenge_id,),
            )
            return True

        challenge = _LOCAL_OTPS.get(email)
        if not challenge or challenge["consumed"] or challenge["expires_at"] <= now:
            return False
        if not secrets.compare_digest(challenge["otp_hash"], otp_hash):
            return False
        challenge["consumed"] = True
        return True

    def _ensure_user(self, email: str) -> CurrentUser:
        tenant_id = safe_tenant_id(email)
        role = settings.auth_default_role
        if settings.database_url:
            self._with_db(
                """
                insert into app_users (email, tenant_id, role, created_at, last_login_at)
                values (%s, %s, %s, now(), now())
                on conflict (email)
                do update set last_login_at = excluded.last_login_at
                """,
                (email, tenant_id, role),
            )
            rows = self._fetch_db(
                "select email, tenant_id, role from app_users where email = %s",
                (email,),
            )
            if rows:
                return CurrentUser(email=rows[0][0], tenant_id=rows[0][1], role=rows[0][2])
        return CurrentUser(email=email, tenant_id=tenant_id, role=role)

    def _store_session(self, token: str, user: CurrentUser, expires_at: datetime) -> None:
        token_hash = self._hash_secret(token)
        if settings.database_url:
            self._with_db(
                """
                insert into auth_sessions (session_hash, email, tenant_id, role, expires_at, created_at)
                values (%s, %s, %s, %s, %s, now())
                """,
                (token_hash, user.email, user.tenant_id, user.role, expires_at),
            )
            return
        _LOCAL_SESSIONS[token_hash] = user

    def _get_session(self, token: str) -> CurrentUser | None:
        token_hash = self._hash_secret(token)
        if settings.database_url:
            rows = self._fetch_db(
                """
                select email, tenant_id, role
                from auth_sessions
                where session_hash = %s
                  and revoked_at is null
                  and expires_at > now()
                limit 1
                """,
                (token_hash,),
            )
            if not rows:
                return None
            return CurrentUser(email=rows[0][0], tenant_id=rows[0][1], role=rows[0][2])
        return _LOCAL_SESSIONS.get(token_hash)

    def _delete_session(self, token: str) -> None:
        token_hash = self._hash_secret(token)
        if settings.database_url:
            self._with_db(
                "update auth_sessions set revoked_at = now() where session_hash = %s",
                (token_hash,),
            )
            return
        _LOCAL_SESSIONS.pop(token_hash, None)

    def _send_otp_email(self, email: str, otp: str) -> None:
        if settings.email_provider.lower() == "ses":
            self._send_otp_email_ses(email, otp)
            return

        if not settings.smtp_host:
            if settings.environment.lower() == "production" and not settings.otp_dev_mode:
                raise HTTPException(
                    status_code=500,
                    detail="SMTP is not configured for OTP delivery.",
                )
            return

        message = EmailMessage()
        message["Subject"] = "Your CA Agentic AI sign-in OTP"
        message["From"] = settings.otp_email_from
        message["To"] = email
        message.set_content(
            "Your one-time password for CA Agentic AI is:\n\n"
            f"{otp}\n\n"
            f"This code expires in {settings.otp_ttl_minutes} minutes. "
            "If you did not request this code, you can ignore this email."
        )

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)

    def _send_otp_email_ses(self, email: str, otp: str) -> None:
        from_email = (settings.ses_from_email or settings.otp_email_from or "").strip()
        if not from_email:
            if settings.environment.lower() == "production" and not settings.otp_dev_mode:
                raise HTTPException(
                    status_code=500,
                    detail="SES sender email is not configured for OTP delivery.",
                )
            return

        subject = "Your LedgerMind AI sign-in OTP"
        body = (
            "Your one-time password for LedgerMind AI is:\n\n"
            f"{otp}\n\n"
            f"This code expires in {settings.otp_ttl_minutes} minutes. "
            "If you did not request this code, you can ignore this email."
        )
        try:
            self._ses_client().send_email(
                FromEmailAddress=from_email,
                Destination={"ToAddresses": [email]},
                Content={
                    "Simple": {
                        "Subject": {"Data": subject, "Charset": "UTF-8"},
                        "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                    }
                },
            )
        except Exception as exc:
            if settings.environment.lower() == "production" and not settings.otp_dev_mode:
                raise HTTPException(
                    status_code=503,
                    detail="OTP email delivery failed. Please verify signup status and try again.",
                ) from exc

    def _ses_client(self):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("Install cloud dependencies with: pip install -e '.[dev,cloud]'") from exc

        return boto3.client("sesv2", region_name=settings.ses_region or settings.aws_region)

    def _verification_required(self) -> bool:
        return bool(settings.auth_require_email_verification)

    def _email_verified(self, email: str) -> bool:
        status = self._email_verification_status(email)
        if status == "SUCCESS":
            self._ensure_user(email)
            return True
        return False

    def _email_verification_status(self, email: str) -> str:
        provider = settings.email_provider.lower()
        if provider == "ses":
            try:
                status = str(
                    self._ses_client()
                    .get_email_identity(EmailIdentity=email)
                    .get("VerificationStatus")
                    or "NOT_STARTED"
                ).upper()
                self._save_email_verification(
                    email,
                    status,
                    provider="ses",
                    detail="SES identity status checked.",
                )
                return status
            except Exception:
                stored = self._stored_email_verification_status(email)
                return stored or "UNKNOWN"
        return self._stored_email_verification_status(email) or "NOT_STARTED"

    def _stored_email_verification_status(self, email: str) -> str | None:
        if settings.database_url:
            rows = self._fetch_db(
                "select status from auth_email_verifications where email = %s",
                (email,),
            )
            if rows:
                return str(rows[0][0]).upper()
            return None

        record = _LOCAL_EMAIL_VERIFICATIONS.get(email)
        return str(record["status"]).upper() if record else None

    def _save_email_verification(
        self,
        email: str,
        status: str,
        *,
        provider: str,
        detail: str,
    ) -> None:
        normalized_status = status.upper()
        verified = normalized_status in {"SUCCESS", "VERIFIED"}
        if settings.database_url:
            self._with_db(
                """
                insert into auth_email_verifications
                    (email, status, provider, requested_at, verified_at, last_checked_at, detail)
                values (%s, %s, %s, now(), case when %s then now() else null end, now(), %s)
                on conflict (email)
                do update set
                    status = excluded.status,
                    provider = excluded.provider,
                    verified_at = case
                        when excluded.verified_at is not null then excluded.verified_at
                        else auth_email_verifications.verified_at
                    end,
                    last_checked_at = excluded.last_checked_at,
                    detail = excluded.detail
                """,
                (email, normalized_status, provider, verified, detail),
            )
            return

        existing = _LOCAL_EMAIL_VERIFICATIONS.get(email, {})
        _LOCAL_EMAIL_VERIFICATIONS[email] = {
            "status": normalized_status,
            "provider": provider,
            "requested_at": existing.get("requested_at") or datetime.now(UTC),
            "verified_at": datetime.now(UTC) if verified else existing.get("verified_at"),
            "last_checked_at": datetime.now(UTC),
            "detail": detail,
        }

    def _with_db(self, query: str, params: tuple[Any, ...]) -> None:
        self._ensure_tables()
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Install cloud dependencies with: pip install -e '.[dev,cloud]'") from exc

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
            conn.commit()

    def _fetch_db(self, query: str, params: tuple[Any, ...]) -> list[tuple[Any, ...]]:
        self._ensure_tables()
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Install cloud dependencies with: pip install -e '.[dev,cloud]'") from exc

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def _ensure_tables(self) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Install cloud dependencies with: pip install -e '.[dev,cloud]'") from exc

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table if not exists app_users (
                        email text primary key,
                        tenant_id text not null,
                        role text not null,
                        created_at timestamptz not null,
                        last_login_at timestamptz not null
                    )
                    """
                )
                cur.execute(
                    """
                    create table if not exists auth_otp_challenges (
                        id bigserial primary key,
                        email text not null,
                        otp_hash text not null,
                        expires_at timestamptz not null,
                        consumed_at timestamptz,
                        created_at timestamptz not null
                    )
                    """
                )
                cur.execute(
                    """
                    create table if not exists auth_sessions (
                        id bigserial primary key,
                        session_hash text unique not null,
                        email text not null,
                        tenant_id text not null,
                        role text not null,
                        expires_at timestamptz not null,
                        revoked_at timestamptz,
                        created_at timestamptz not null
                    )
                    """
                )
                cur.execute(
                    """
                    create table if not exists auth_email_verifications (
                        email text primary key,
                        status text not null,
                        provider text not null,
                        requested_at timestamptz not null,
                        verified_at timestamptz,
                        last_checked_at timestamptz,
                        detail text not null default ''
                    )
                    """
                )
            conn.commit()

    def _hash_secret(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_reviewer(user: CurrentUser | None) -> bool:
    return bool(user and user.role in {"admin", "reviewer"})
