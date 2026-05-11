import base64
import io
import zipfile


def pack_invoice(xml: bytes, filename_base: str) -> bytes:
    """Empaca el XML firmado en un ZIP con un solo entry {filename_base}.xml.

    SUNAT espera el XML dentro de un ZIP con el mismo nombre base.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{filename_base}.xml", xml)
    return buf.getvalue()


def unpack_cdr(b64_zip: str | bytes) -> bytes:
    """Decodifica el applicationResponse de SUNAT y devuelve el XML del CDR.

    Zeep auto-decodifica xsd:base64Binary, asi que en runtime suele llegar
    como bytes ZIP crudos (PK..). Soportamos ambos formatos.
    """
    if isinstance(b64_zip, bytes) and b64_zip[:2] == b"PK":
        zip_bytes = b64_zip
    else:
        raw = b64_zip.encode("ascii") if isinstance(b64_zip, str) else b64_zip
        zip_bytes = base64.b64decode(raw)

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for name in zf.namelist():
            if name.endswith(".xml"):
                return zf.read(name)
    raise RuntimeError("CDR ZIP no contiene XML")
