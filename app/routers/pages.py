from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.templates import templates

router = APIRouter()


@router.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
