"""
Upload de arquivos — imagens, áudios e arquivos genéricos.

Estratégia de storage:
  - Se CLOUDINARY_URL (ou CLOUDINARY_CLOUD_NAME + KEY + SECRET) estiver definido:
      → faz upload para Cloudinary e retorna URL pública persistente.
  - Caso contrário (dev local):
      → salva em disco (pasta /uploads/) e retorna URL relativa.
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.dependencies import get_current_user
from app.core.cloudinary_service import is_cloudinary_enabled, upload_bytes, upload_bytes_raw

router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg", "audio/ogg", "audio/webm",
    "audio/wav", "audio/mp4", "audio/x-m4a",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024    # 5 MB
MAX_AUDIO_SIZE = 20 * 1024 * 1024   # 20 MB
MAX_FILE_SIZE  = 10 * 1024 * 1024   # 10 MB

EXT_MAP = {
    "image/jpeg": ".jpg", "image/png": ".png",
    "image/webp": ".webp", "image/gif": ".gif",
    "audio/mpeg": ".mp3", "audio/ogg": ".ogg",
    "audio/webm": ".webm", "audio/wav": ".wav",
    "audio/mp4": ".m4a", "audio/x-m4a": ".m4a",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _save_local(content: bytes, ext: str) -> str:
    """Salva em disco local e retorna a URL relativa /uploads/..."""
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(content)
    return f"/uploads/{filename}"


def _upload_image(content: bytes, content_type: str) -> str:
    if is_cloudinary_enabled():
        return upload_bytes(content, folder="leaf/images", resource_type="image")
    return _save_local(content, EXT_MAP.get(content_type, ".jpg"))


def _upload_audio(content: bytes, content_type: str) -> str:
    if is_cloudinary_enabled():
        return upload_bytes_raw(content, folder="leaf/audio")
    return _save_local(content, EXT_MAP.get(content_type, ".ogg"))


def _upload_file(content: bytes, filename: str) -> str:
    if is_cloudinary_enabled():
        return upload_bytes_raw(content, folder="leaf/files")
    safe = filename or f"{uuid.uuid4().hex}.bin"
    path = os.path.join(UPLOAD_DIR, safe)
    with open(path, "wb") as f:
        f.write(content)
    return f"/uploads/{safe}"


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx 10 MB)")
    url = _upload_file(content, file.filename or "")
    return {"filename": file.filename, "url": url}


@router.post("/file")
async def upload_file_named(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx 10 MB)")
    url = _upload_file(content, file.filename or "")
    return {"url": url}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    _user=Depends(get_current_user),
):
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de imagem não suportado: '{content_type}'. Use jpg, png, webp ou gif.",
        )
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Imagem muito grande (máx 5 MB)")

    if is_cloudinary_enabled():
        url = upload_bytes(content, folder="leaf/avatars", resource_type="image")
    else:
        url = _save_local(content, EXT_MAP.get(content_type, ".jpg"))

    return {"url": url}


@router.post("/image")
async def upload_chat_image(
    file: UploadFile = File(...),
    _user=Depends(get_current_user),
):
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de imagem não suportado: '{content_type}'. Use jpg, png, webp ou gif.",
        )
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Imagem muito grande (máx 5 MB)")
    return {"url": _upload_image(content, content_type)}


@router.post("/audio")
async def upload_chat_audio(
    file: UploadFile = File(...),
    _user=Depends(get_current_user),
):
    # MediaRecorder envia "audio/webm;codecs=opus" — remover parâmetros
    # antes de comparar, senão nunca casa com "audio/webm".
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de áudio não suportado: '{content_type}'. Use mp3, ogg, webm, wav ou m4a.",
        )
    content = await file.read()
    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="Áudio muito grande (máx 20 MB)")
    return {"url": _upload_audio(content, content_type)}
