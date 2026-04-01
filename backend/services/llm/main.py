from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from ollama._types import ResponseError

from config import settings
from schemas import ParseRequest, ParseResponse
from services.ollama_service import OllamaParserService
from services.openrouter_service import OpenRouterParserService

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


def get_parser_service() -> OllamaParserService:
    return OllamaParserService()


def get_openrouter_service() -> OpenRouterParserService:
    return OpenRouterParserService()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


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