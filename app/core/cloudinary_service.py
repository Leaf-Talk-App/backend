"""
Serviço de upload via Cloudinary.
Fallback para disco local se as credenciais não estiverem configuradas.

IMPORTANTE: as credenciais vêm de `settings` (pydantic, carregado de .env),
NÃO de os.environ. pydantic-settings lê o .env para o objeto Settings mas
não exporta as variáveis para os.environ — por isso usamos settings.* aqui.
"""
import uuid
import cloudinary
import cloudinary.uploader
from app.core.config import settings

_configured = False


def _ensure_configured():
    global _configured
    if _configured:
        return

    if settings.CLOUDINARY_URL:
        # CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME — configuração automática
        cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
    elif (
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    ):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    _configured = True


def is_cloudinary_enabled() -> bool:
    """True se Cloudinary está configurado."""
    return bool(
        settings.CLOUDINARY_URL
        or (
            settings.CLOUDINARY_CLOUD_NAME
            and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_SECRET
        )
    )


def upload_bytes(
    content: bytes,
    *,
    folder: str = "leaf",
    resource_type: str = "auto",
    public_id: str | None = None,
) -> str:
    """
    Faz upload de bytes para Cloudinary e retorna a URL segura.
    resource_type: "image" | "video" | "raw" | "auto"
    """
    _ensure_configured()

    # public_id NÃO deve incluir o folder — o Cloudinary o prefixa via `folder=`.
    # Antes gerava `leaf/images/leaf/images/<hex>` (folder duplicado).
    pid = public_id or uuid.uuid4().hex

    result = cloudinary.uploader.upload(
        content,
        folder=folder,
        public_id=pid,
        resource_type=resource_type,
        overwrite=True,
        # Otimização automática de qualidade e formato para imagens
        transformation=[{"quality": "auto", "fetch_format": "auto"}]
        if resource_type in ("image", "auto")
        else [],
    )

    return result["secure_url"]


def upload_bytes_raw(content: bytes, *, folder: str = "leaf/audio", ext: str = "") -> str:
    """Upload de áudio/arquivo sem transformação (resource_type=raw).

    `ext` (ex.: ".pdf", ".docx") é anexado ao public_id para que a URL final
    termine com a extensão correta. Sem isso, o Cloudinary serve o arquivo raw
    sem extensão → o download vem num "formato nada a ver" (o SO não reconhece o
    tipo) e a detecção de PDF no front falha.
    """
    _ensure_configured()
    ext = (ext or "").strip().lower()
    if ext and not ext.startswith("."):
        ext = "." + ext
    pid = uuid.uuid4().hex + ext
    result = cloudinary.uploader.upload(
        content,
        folder=folder,
        resource_type="raw",
        public_id=pid,
    )
    return result["secure_url"]
