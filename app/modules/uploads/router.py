from fastapi import APIRouter, UploadFile, File
import os
import uuid

router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"]
)

UPLOAD_DIR = "storage"

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as buffer:
        buffer.write(await file.read())

    return {
        "url": f"/storage/{filename}"
    }