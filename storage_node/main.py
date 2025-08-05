from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Annotated, cast
from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile, status
from starlette.responses import FileResponse
from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError

class Settings(BaseSettings):
    fs_base_path: Path = Field(...)
    chunk_size: int = 8192

def get_env(request: Request) -> Settings:
    return cast(Settings, request.state.env)

Env = Annotated[Settings, Depends(get_env)]

def root_in_fs(relative: str, env: Env) -> Path:
    full_path = (env.fs_base_path / relative).resolve()
    if not full_path.is_relative_to(env.fs_base_path.resolve()):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Storage node is forbidden to access the outside of designated root folder"
        )
    return full_path

@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        settings = Settings()
    except ValidationError as ex:
        missing_vars = ", ".join(
            cast(str, error["loc"][0]).upper()
            for error in ex.errors()
            if error["type"] == "missing"
        )
        raise Exception(f"Missing {missing_vars} environment variable(s)") from ex

    yield {"env": settings}

app = FastAPI(lifespan=lifespan)


@app.get("/file/{path:path}")
async def file_get(path: str, response: Response, env: Env):
    full_path = root_in_fs(path, env)
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

@app.put("/file/{path:path}")
async def file_set(path: str, file: UploadFile, env: Env):
    full_path = root_in_fs(path, env)
    # TODO handle mkdir over an existing file
    full_path.parent.mkdir(parents=True, exist_ok=True)

    with open(full_path, "wb") as buffer:
        while chunk := await file.read(env.chunk_size):
            _ = buffer.write(chunk)

    return {"status": "success"}

@app.delete("/file/{path:path}")
async def file_delete(path: str, env: Env):
    full_path = root_in_fs(path, env)

    if full_path == env.fs_base_path.resolve():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Root folder deletion is forbidden")

    if not full_path.exists():
        raise HTTPException(status.HTTP_409_CONFLICT, "File does not exist")
    
    if full_path.is_dir():
        if next(full_path.iterdir(), None):  # TODO recursive flag?
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Directory is not empty")
        os.rmdir(full_path)
    else:
        os.remove(full_path)

    return {"status": "success"}

