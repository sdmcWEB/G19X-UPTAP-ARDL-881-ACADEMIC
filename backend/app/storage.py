import io

from minio import Minio

from app.config import settings

_client: Minio | None = None


def client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def ensure_bucket() -> None:
    c = client()
    if not c.bucket_exists(settings.minio_bucket):
        c.make_bucket(settings.minio_bucket)


def put(object_key: str, data: bytes, content_type: str) -> None:
    ensure_bucket()
    client().put_object(
        settings.minio_bucket,
        object_key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def get(object_key: str) -> bytes:
    resp = client().get_object(settings.minio_bucket, object_key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()
