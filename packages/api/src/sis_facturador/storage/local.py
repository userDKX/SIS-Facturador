from pathlib import Path

from sis_facturador.config import settings

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_dir() -> Path:
    if settings.LOCAL_STORAGE_DIR:
        return Path(settings.LOCAL_STORAGE_DIR).expanduser().resolve()
    return _REPO_ROOT / "storage"


def _write(path: str, content: bytes) -> str:
    """Escribe el archivo y devuelve un URI file:// absoluto."""
    target = _resolve_dir() / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return f"file://{target.as_posix()}"


def upload_xml(path: str, content: bytes) -> str:
    return _write(path, content)


def upload_cdr(path: str, content: bytes) -> str:
    return _write(path, content)
