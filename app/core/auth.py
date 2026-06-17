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
    def request_otp(self, email: str) -> dict[str, Any]:
        normalized_email = OTPRequest(email=email).email
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
            conn.commit()

    def _hash_secret(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_reviewer(user: CurrentUser | None) -> bool:
    return bool(user and user.role in {"admin", "reviewer"})
