from __future__ import annotations

import json
import re

import cohere
import httpx
from cohere.core.api_error import ApiError
from cohere.errors import (
    ForbiddenError,
    GatewayTimeoutError,
    InvalidTokenError,
    TooManyRequestsError,
    UnauthorizedError,
)
from pydantic import ValidationError

from ai.prompts import SYSTEM_PROMPT
from ai.schemas import AIAnalysis, ResearchSnapshot


class AIConfigurationError(RuntimeError):
    pass


class AIAnalysisError(RuntimeError):
    pass


def build_input(snapshot: ResearchSnapshot) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "ResearchSnapshot JSON:\n" + snapshot.model_dump_json(indent=2),
        },
    ]


def _assert_missing_metrics_not_invented(snapshot: ResearchSnapshot, analysis: AIAnalysis) -> None:
    text = json.dumps(analysis.model_dump(), ensure_ascii=False)
    checks = {
        "P/E": snapshot.fundamentals.pe_ratio,
        "P/B": snapshot.fundamentals.pb_ratio,
        "debt-to-equity": snapshot.fundamentals.debt_to_equity,
        "RSI": snapshot.technical.rsi_14,
        "beta": snapshot.risk.beta,
    }
    for label, value in checks.items():
        if value is None and re.search(rf"{re.escape(label)}[^.\n]{{0,40}}\d", text, re.IGNORECASE):
            raise AIAnalysisError(f"AI response supplied a numeric {label} although it was unavailable")


def generate_research_analysis(
    snapshot: ResearchSnapshot, api_key: str, model: str, timeout: int = 30
) -> AIAnalysis:
    if not api_key:
        raise AIConfigurationError("COHERE_API_KEY is not configured in .env")
    try:
        client = cohere.ClientV2(api_key=api_key, timeout=timeout, max_retries=1)
        response = client.chat(
            model=model,
            messages=build_input(snapshot),
            response_format={
                "type": "json_object",
                "schema": AIAnalysis.model_json_schema(),
            },
        )
        content = getattr(getattr(response, "message", None), "content", None)
        if not content:
            raise AIAnalysisError("Cohere did not return analysis content")
        first_block = content[0]
        text = first_block.get("text") if isinstance(first_block, dict) else getattr(first_block, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise AIAnalysisError("Cohere returned malformed analysis content")
        parsed = AIAnalysis.model_validate(json.loads(text))
        _assert_missing_metrics_not_invented(snapshot, parsed)
        return parsed
    except (AIConfigurationError, AIAnalysisError):
        raise
    except (InvalidTokenError, UnauthorizedError, ForbiddenError) as exc:
        raise AIConfigurationError("Cohere rejected the configured API key") from exc
    except TooManyRequestsError as exc:
        raise AIAnalysisError("Cohere rate limit reached; try again later") from exc
    except (GatewayTimeoutError, httpx.TimeoutException) as exc:
        raise AIAnalysisError("Cohere request timed out; try again later") from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AIAnalysisError("Cohere returned an invalid structured analysis") from exc
    except ApiError as exc:
        raise AIAnalysisError("The Cohere analysis service is currently unavailable") from exc
    except Exception as exc:
        raise AIAnalysisError("The Cohere analysis service is currently unavailable") from exc
