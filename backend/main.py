"""اپلیکیشن FastAPI: بارگذاری فایل، کاتالوگ سؤالات و اجرای تحلیل‌ها."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import analytics
from .catalog import QUESTION_BY_ID, catalog_payload
from .ingest import read_excel, summarize
from .schema import CURRENCY_LABEL, SchemaError
from .store import store

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
SAMPLE_FILE = ROOT / "data" / "sample.xlsx"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

app = FastAPI(title="داشبورد تحلیل جذب و استخدام", docs_url=None, redoc_url=None)


@app.exception_handler(SchemaError)
async def schema_error_handler(_: Request, exc: SchemaError) -> JSONResponse:
    return JSONResponse(status_code=422, content=exc.to_dict())


def _session_payload(session) -> dict:
    return {
        "session_id": session.id,
        "summary": session.summary,
        "currency": CURRENCY_LABEL,
    }


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    name = (file.filename or "").lower()
    if not name.endswith((".xlsx", ".xlsm")):
        raise SchemaError(
            "فرمت فایل پشتیبانی نمی‌شود.",
            detail="لطفاً یک فایل اکسل با پسوند xlsx بارگذاری کنید.",
        )

    content = await file.read()
    if not content:
        raise SchemaError("فایل خالی است.", detail="محتوایی برای خواندن یافت نشد.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise SchemaError(
            "حجم فایل بیش از حد مجاز است.",
            detail=f"حداکثر حجم مجاز {MAX_UPLOAD_BYTES // (1024 * 1024)} مگابایت است.",
        )

    df = read_excel(content)
    session = store.create(df, summarize(df))
    return _session_payload(session)


@app.post("/api/sample")
async def load_sample() -> dict:
    if not SAMPLE_FILE.exists():
        raise HTTPException(status_code=404, detail="فایل داده نمونه در پوشه data یافت نشد.")
    df = read_excel(SAMPLE_FILE.read_bytes())
    session = store.create(df, summarize(df))
    return _session_payload(session)


@app.get("/api/questions")
async def questions(session_id: str = Query(default="")) -> dict:
    payload = catalog_payload()
    session = store.get(session_id)
    payload["summary"] = session.summary if session else None
    payload["currency"] = CURRENCY_LABEL
    return payload


@app.get("/api/questions/{qid}")
async def question_detail(qid: str, request: Request, session_id: str = Query(...)) -> dict:
    question = QUESTION_BY_ID.get(qid)
    if question is None:
        raise HTTPException(status_code=404, detail="این سؤال در کاتالوگ وجود ندارد.")

    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="نشست شما منقضی شده است. لطفاً فایل را دوباره بارگذاری کنید.")

    params = {k: v for k, v in request.query_params.items() if k != "session_id"}

    if qid == "p1":
        payload = _run_predictive(session, params)
    else:
        handler = analytics.HANDLERS.get(qid)
        if handler is None:
            raise HTTPException(status_code=501, detail="تحلیل این سؤال هنوز پیاده‌سازی نشده است.")
        payload = handler(session.df, params)

    payload["meta"] = question.meta()
    payload["currency"] = CURRENCY_LABEL
    return payload


def _run_predictive(session, params: dict) -> dict:
    """مدل یک‌بار در هر نشست آموزش می‌بیند و سپس از کش خوانده می‌شود."""
    from .analytics import predictive

    bundle = session.cache.get("p1_model")
    if bundle is None:
        try:
            bundle = predictive.train_model(session.df)
        except Exception as exc:  # داده ناکافی یا تک‌مقداری برای آموزش
            raise HTTPException(
                status_code=422,
                detail=f"آموزش مدل روی این داده ممکن نشد: {exc}",
            ) from exc
        session.cache["p1_model"] = bundle
    return predictive.p1_time_to_fill_forecast(session.df, params, bundle)


@app.post("/api/predict/time-to-fill")
async def predict_time_to_fill(payload: dict) -> dict:
    from .analytics import predictive

    session = store.get(payload.get("session_id"))
    if session is None:
        raise HTTPException(status_code=401, detail="نشست شما منقضی شده است. لطفاً فایل را دوباره بارگذاری کنید.")

    bundle = session.cache.get("p1_model")
    if bundle is None:
        bundle = predictive.train_model(session.df)
        session.cache["p1_model"] = bundle
    return predictive.predict_payload(bundle, payload)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
