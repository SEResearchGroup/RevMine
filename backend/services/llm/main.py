import json
import logging
import time
import traceback
from datetime import datetime, timezone as dt_timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from ollama._types import ResponseError

from config import settings
from schemas import ParseRequest, ParseResponse
from services.ollama_service import OllamaParserService
from services.openrouter_service import OpenRouterParserService


# ---------------------------------------------------------------------------
# Structured JSON logging setup
# ---------------------------------------------------------------------------

class _JSONFormatter(logging.Formatter):
    _RESERVED = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "taskName",
        "message", "asctime",
    })

    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=dt_timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "llm",
            "logger": record.name,
            "message": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k not in self._RESERVED:
                obj[k] = v
        if record.exc_info:
            obj["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }
        return json.dumps(obj, default=str, ensure_ascii=False)


_handler = logging.StreamHandler()
_handler.setFormatter(_JSONFormatter())
logging.basicConfig(handlers=[_handler], level=logging.INFO, force=True)
# Silence noisy uvicorn access logs (replaced by our middleware below)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


@app.middleware("http")
async def _request_logging_middleware(request: Request, call_next):
    """Log every HTTP request with method, path, status code and duration."""
    _start = time.monotonic()
    response = await call_next(request)
    duration = round(time.monotonic() - _start, 3)
    logger.info(
        "HTTP request handled",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration": duration,
            "event": "http_request",
        },
    )
    return response


def get_parser_service() -> OllamaParserService:
    return OllamaParserService()


def get_openrouter_service() -> OpenRouterParserService:
    return OpenRouterParserService()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/models")
def get_available_models() -> dict:
    """Return the list of available LLM providers and their models."""
    return {
        "openrouter": {
            "default": settings.OPENROUTER_DEFAULT_MODEL,
            "models": [
                {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini (OpenAI)"},
                {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B (Free)"},
                {"id": "google/gemma-3-4b-it", "name": "Gemma 3 4B (Free)"},
                {"id": "microsoft/phi-3-mini-128k-instruct", "name": "Phi-3 Mini (Free)"},
                {"id": "qwen/qwen3-8b", "name": "Qwen3 8B (Free)"},
                {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1 (Free)"},
            ],
        },
        "ollama": {
            "default": settings.DEFAULT_MODEL,
        },
    }


@app.post("/openrouter", response_model=ParseResponse)
def openrouter_parse_request(
    payload: ParseRequest,
    parser_service: OpenRouterParserService = Depends(get_openrouter_service),
):
    selected_model = payload.model or settings.OPENROUTER_DEFAULT_MODEL

    try:
        result = parser_service.parse_user_request(
            user_message=payload.user_message,
            model=selected_model,
        )
        return ParseResponse(model=selected_model, result=result)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_model_json",
                "message": str(exc),
            },
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {exc}"
        ) from exc


@app.post("/ollama", response_model=ParseResponse)
def parse_request(
    payload: ParseRequest,
    parser_service: OllamaParserService = Depends(get_parser_service),
):
    selected_model = payload.model or settings.DEFAULT_MODEL

    try:
        result = parser_service.parse_user_request(
            user_message=payload.user_message,
            model=selected_model,
        )
        return ParseResponse(model=selected_model, result=result)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_model_json",
                "message": str(exc),
            },
        ) from exc

    except ResponseError as exc:
        raise HTTPException(
            status_code=502, detail=f"Ollama response error: {exc}"
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {exc}"
        ) from exc


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unhandled server error: {str(exc)}"},
    )