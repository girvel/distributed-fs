import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response, UploadFile, status
from starlette.responses import FileResponse

app = FastAPI()

FS_BASE_PATH = Path(".fs")
CHUNK_SIZE = 8192

@app.get("/{file_path:path}")
async def get_file(file_path: str, response: Response):
    full_path = FS_BASE_PATH / file_path
    if not full_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File does not exist")

    if full_path.is_file():
        response.headers["X-Item-Type"] = "file"  # TODO document header
        return FileResponse(full_path)

    response.headers["X-Item-Type"] = "directory"
    return {
        "items": os.listdir(full_path),
        # TODO also return is it file/directory
    }

@app.put("/{file_path:path}")
async def set_file(file_path: str, file: UploadFile):
    full_path = FS_BASE_PATH / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    with open(full_path, "wb") as buffer:
        while chunk := await file.read(CHUNK_SIZE):
            _ = buffer.write(chunk)

    return {"status": "success"}

