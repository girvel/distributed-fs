import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response, status
from starlette.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# TODO env configuration
FS_BASE_PATH = Path("./fs/")

class DirectoryListing(BaseModel):
    items: list[str]

# TODO list directories
# TODO test for paths such as ../../etc/passwd
@app.get("/{file_path:path}", response_model=DirectoryListing | None)
async def get_file(file_path: str, response: Response):
    full_path = FS_BASE_PATH / file_path
    if not full_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    if full_path.is_file():
        response.headers["X-Item-Type"] = "file"  # TODO document header
        return FileResponse(full_path)

    response.headers["X-Item-Type"] = "directory"
    return {
        "items": os.listdir(full_path),
        # TODO also return is it file/directory
        # TODO cache response
    }

