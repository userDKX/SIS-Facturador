from sis_facturador.config import settings
from sis_facturador.storage import local as _local
from sis_facturador.storage import supabase_client as _sb


def upload_xml(path: str, content: bytes) -> str:
    if settings.STORAGE_BACKEND == "supabase":
        return _sb.upload_xml(path, content)
    return _local.upload_xml(path, content)


def upload_cdr(path: str, content: bytes) -> str:
    if settings.STORAGE_BACKEND == "supabase":
        return _sb.upload_cdr(path, content)
    return _local.upload_cdr(path, content)
