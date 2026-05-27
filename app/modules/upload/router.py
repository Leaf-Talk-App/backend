import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/ogg", "audio/webm", "audio/wav", "audio/mp4", "audio/x-m4a"}

MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5 MB
MAX_AUDIO_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_FILE_SIZE  = 10 * 1024 * 1024  # 10 MB

EXT_MAP = {
    "image/jpeg":  ".jpg",
    "image/png":   ".png",
    "image/webp":  ".webp",
    "image/gif":   ".gif",
    "audio/mpeg":  ".mp3",
    "audio/ogg":   ".ogg",
    "audio/webm":  ".webm",
    "audio/wav":   ".wav",
    "audio/mp4":   ".m4a",
    "audio/x-m4a": ".m4a",
}


def _save(file_content: bytes, ext: str) -> str:
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    return filename


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    file_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    return {"filename": file.filename, "url": f"/uploads/{file.filename}"}


@router.post("/file")
async def upload_file_named(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    file_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    return {"url": f"/uploads/{file.filename}"}


@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type '{content_type}'. Allowed: jpg, png, webp, gif"
        )
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image too large (max 5 MB)")
    ext = EXT_MAP.get(content_type, ".jpg")
    filename = _save(content, ext)
    return {"url": f"/uploads/{filename}"}


@router.post("/image")
async def upload_chat_image(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type '{content_type}'. Allowed: jpg, png, webp, gif"
        )
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image too large (max 5 MB)")
    ext = EXT_MAP.get(content_type, ".jpg")
    filename = _save(content, ext)
    return {"url": f"/uploads/{filename}"}


@router.post("/audio")
async def upload_chat_audio(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio type '{content_type}'. Allowed: mp3, ogg, webm, wav, m4a"
        )
    content = await file.read()
    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="Audio too large (max 20 MB)")
    ext = EXT_MAP.get(content_type, ".ogg")
    filename = _save(content, ext)
    return {"url": f"/uploads/{filename}"}
