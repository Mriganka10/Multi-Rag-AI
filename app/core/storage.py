from pathlib import Path

from app.core.audit import safe_tenant_id
from app.core.config import settings


class UploadStorage:
    def persist_upload(
        self,
        *,
        local_path: Path,
        tenant_id: str,
        original_filename: str,
    ) -> str:
        if settings.storage_provider.lower() != "s3":
            return str(local_path)

        if not settings.s3_bucket:
            raise RuntimeError("STORAGE_PROVIDER=s3 requires S3_BUCKET to be configured.")

        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError(
                "STORAGE_PROVIDER=s3 is configured, but boto3 is not installed. "
                "Install cloud dependencies with pip install -e '.[cloud]'."
            ) from exc

        tenant = safe_tenant_id(tenant_id)
        clean_name = Path(original_filename or local_path.name).name
        key = f"{settings.s3_prefix.strip('/')}/tenants/{tenant}/uploads/{local_path.name}-{clean_name}"

        extra_args: dict[str, str] = {"ServerSideEncryption": "AES256"}
        if settings.s3_kms_key_id:
            extra_args = {
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": settings.s3_kms_key_id,
            }

        client = boto3.client("s3", region_name=settings.aws_region)
        client.upload_file(
            Filename=str(local_path),
            Bucket=settings.s3_bucket,
            Key=key,
            ExtraArgs=extra_args,
        )
        return f"s3://{settings.s3_bucket}/{key}"

    def persist_artifact(
        self,
        *,
        local_path: Path,
        tenant_id: str,
        artifact_id: str,
    ) -> str:
        if settings.storage_provider.lower() != "s3":
            return str(local_path)

        if not settings.s3_bucket:
            raise RuntimeError("STORAGE_PROVIDER=s3 requires S3_BUCKET to be configured.")

        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError(
                "STORAGE_PROVIDER=s3 is configured, but boto3 is not installed. "
                "Install cloud dependencies with pip install -e '.[cloud]'."
            ) from exc

        tenant = safe_tenant_id(tenant_id)
        key = (
            f"{settings.s3_prefix.strip('/')}/tenants/{tenant}/artifacts/"
            f"{artifact_id}/{local_path.name}"
        )
        extra_args: dict[str, str] = {
            "ServerSideEncryption": "AES256",
            "ContentType": _content_type(local_path.suffix),
        }
        if settings.s3_kms_key_id:
            extra_args.update(
                {
                    "ServerSideEncryption": "aws:kms",
                    "SSEKMSKeyId": settings.s3_kms_key_id,
                }
            )

        client = boto3.client("s3", region_name=settings.aws_region)
        client.upload_file(
            Filename=str(local_path),
            Bucket=settings.s3_bucket,
            Key=key,
            ExtraArgs=extra_args,
        )
        return f"s3://{settings.s3_bucket}/{key}"


def _content_type(suffix: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(suffix.lower(), "application/octet-stream")
