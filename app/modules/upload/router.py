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
import mimetypes
import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse, Response
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

# Lista branca p/ o upload genérico de arquivo: imagens, pdf, docx/doc, zip, txt.
ALLOWED_FILE_TYPES = ALLOWED_IMAGE_TYPES | {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/msword",  # doc
    "application/zip",
    "application/x-zip-compressed",
    "text/plain",
}

# Extensões executáveis/perigosas — bloqueadas independente do MIME informado.
BLOCKED_EXTS = {
    ".exe", ".sh", ".bat", ".cmd", ".com", ".js", ".mjs", ".jar", ".msi",
    ".dll", ".scr", ".ps1", ".vbs", ".apk", ".app", ".bin", ".deb", ".rpm",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024    # 5 MB
MAX_AUDIO_SIZE = 20 * 1024 * 1024   # 20 MB
MAX_FILE_SIZE  = 10 * 1024 * 1024   # 10 MB


def _validate_file(file: UploadFile, content: bytes) -> None:
    """Valida tamanho, bloqueia executáveis (por extensão) e checa o MIME contra
    a lista branca. Não confia só na extensão — usa o content_type também."""
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx 10 MB)")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext in BLOCKED_EXTS:
        raise HTTPException(status_code=415, detail=f"Tipo de arquivo não permitido: {ext}")
    ctype = (file.content_type or "").split(";")[0].strip().lower()
    if ctype and ctype not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=415, detail=f"Tipo de arquivo não suportado: {ctype}")

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
    ext = EXT_MAP.get(content_type, ".ogg")
    if is_cloudinary_enabled():
        return upload_bytes_raw(content, folder="leaf/audio", ext=ext)
    return _save_local(content, ext)


def _upload_file(content: bytes, filename: str) -> str:
    # IMPORTANTE: NÃO colocar a extensão real no public_id do Cloudinary.
    # O Cloudinary BLOQUEIA a entrega de .pdf/.zip por padrão (HTTP 400). Sem a
    # extensão, o arquivo é servido como raw genérico (liberado) — o download
    # volta com o nome/tipo certos pelo proxy /upload/download (Content-
    # Disposition). DOCX já funcionava; assim PDF/ZIP também funcionam.
    ext = os.path.splitext(filename or "")[1].lower() or ".bin"
    if is_cloudinary_enabled():
        return upload_bytes_raw(content, folder="leaf/files", ext="")
    # Nome SEMPRE em UUID gerado pelo servidor, nunca o nome do usuário — evita
    # path traversal (../) e colisão de nomes.
    safe = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, safe)
    with open(path, "wb") as f:
        f.write(content)
    return f"/uploads/{safe}"


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/")
async def upload_file(file: UploadFile = File(...), _user=Depends(get_current_user)):
    content = await file.read()
    _validate_file(file, content)
    url = _upload_file(content, file.filename or "")
    return {"filename": file.filename, "url": url}


@router.post("/file")
async def upload_file_named(file: UploadFile = File(...), _user=Depends(get_current_user)):
    content = await file.read()
    _validate_file(file, content)
    url = _upload_file(content, file.filename or "")
    return {"url": url}


@router.get("/download")
async def download_proxy(url: str = Query(...), name: str = Query("arquivo")):
    """Proxy de download: busca o arquivo (Cloudinary/local) e devolve com
    Content-Disposition: attachment → o navegador abre o "salvar como" e nunca
    tenta renderizar inline (corrige PDF/zip que davam erro 400/visualizador)."""
    safe_name = (name or "arquivo").replace('"', "").replace("\n", " ").strip() or "arquivo"

    # arquivo local (dev) — basename remove qualquer "../" (anti path traversal)
    if url.startswith("/uploads/"):
        name_only = os.path.basename(url)
        path = os.path.join(UPLOAD_DIR, name_only)
        if not name_only or not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        return FileResponse(path, filename=safe_name)

    # só permite buscar do Cloudinary (evita SSRF)
    if not url.startswith("https://res.cloudinary.com/"):
        raise HTTPException(status_code=400, detail="URL não permitida")

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as cx:
            r = await cx.get(url)
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao buscar o arquivo")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Falha ao buscar o arquivo")

    # tipo pelo NOME original (o raw do Cloudinary vem sem extensão/genérico)
    guessed, _ = mimetypes.guess_type(safe_name)
    media = guessed or r.headers.get("content-type", "application/octet-stream").split(";")[0]
    headers = {"Content-Disposition": f'attachment; filename="{safe_name}"'}
    return Response(content=r.content, media_type=media, headers=headers)


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
