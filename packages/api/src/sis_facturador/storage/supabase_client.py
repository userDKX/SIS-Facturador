from functools import lru_cache

from supabase import Client, create_client

from sis_facturador.config import settings


@lru_cache
def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _upload(path: str, content: bytes, content_type: str) -> str:
    client = get_supabase()
    bucket = client.storage.from_(settings.SUPABASE_BUCKET)
    bucket.upload(
        path=path,
        file=content,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return bucket.get_public_url(path)


def upload_xml(path: str, content: bytes) -> str:
    return _upload(path, content, "application/xml")


def upload_cdr(path: str, content: bytes) -> str:
    return _upload(path, content, "application/xml")
