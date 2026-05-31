"""
Serviço de upload via Cloudinary.
Fallback para disco local se CLOUDINARY_URL não estiver configurado.
"""
import os
import uuid
import cloudinary
import cloudinary.uploader
from app.core.config import settings

_configured = False


def _ensure_configured():
    global _configured
    if _configured:
        return

    cloudinary_url = os.environ.get("CLOUDINARY_URL", "")
    if cloudinary_url:
        # CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME — configuração automática
        cloudinary.config(cloudinary_url=cloudinary_url)
    else:
        # Configuração manual pelas variáveis individuais
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
        api_key = os.environ.get("CLOUDINARY_API_KEY", "")
        api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")
        if cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True,
            )
        else:
            _configured = True  # sem Cloudinary — usa disco local
            return

    _configured = True


def is_cloudinary_enabled() -> bool:
    """True se Cloudinary está configurado."""
    return bool(
        os.environ.get("CLOUDINARY_URL")
        or (
            os.environ.get("CLOUDINARY_CLOUD_NAME")
            and os.environ.get("CLOUDINARY_API_KEY")
            and os.environ.get("CLOUDINARY_API_SECRET")
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

    pid = public_id or f"{folder}/{uuid.uuid4().hex}"

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


def upload_bytes_raw(content: bytes, *, folder: str = "leaf/audio") -> str:
    """Upload de áudio/arquivo sem transformação."""
    _ensure_configured()
    result = cloudinary.uploader.upload(
        content,
        folder=folder,
        resource_type="raw",
        public_id=f"{folder}/{uuid.uuid4().hex}",
    )
    return result["secure_url"]
