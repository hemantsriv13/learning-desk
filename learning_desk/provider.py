"""The only module that talks to an LLM provider (Anthropic, via the official SDK).

To switch providers, re-implement build_request() and send() with the same
inputs and outputs. Nothing else in the app imports the provider SDK.

Choices made on purpose:
- max_retries=0: the SDK normally retries failed requests automatically. Each
  retry can be billed, so this app makes exactly one attempt per click.
- No server-side model fallback: a fallback would re-run the request on a
  different model (and bill it) without you asking.
- Structured output: the request includes a JSON schema, and the API constrains
  the reply to it. The app still validates the reply itself (see ai.py).
"""

import json
from dataclasses import dataclass, field

import anthropic

from . import config

PROVIDER_NAME = "Anthropic"


@dataclass
class ProviderResponse:
    text: str
    returned_model: str | None
    stop_reason: str | None
    usage: dict | None
    raw: str


@dataclass
class ProviderError(Exception):
    message: str
    raw: str | None = None
    returned_model: str | None = None
    stop_reason: str | None = None
    usage: dict | None = None
    extra: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


def build_request(*, system: str, user_text: str, schema: dict) -> dict:
    """The exact keyword arguments for messages.create(). Contains no credentials."""
    output_config: dict = {"format": {"type": "json_schema", "schema": schema}}
    if config.effort():
        output_config["effort"] = config.effort()
    return {
        "model": config.model(),
        "max_tokens": config.max_tokens(),
        "system": system,
        "messages": [{"role": "user", "content": user_text}],
        "output_config": output_config,
    }


def send(request: dict) -> ProviderResponse:
    """Send one request. Raises ProviderError with a readable message on any failure."""
    if not config.api_key_present():
        raise ProviderError("No API key found. Set ANTHROPIC_API_KEY in your environment or .env file.")

    client = anthropic.Anthropic(max_retries=0, timeout=config.timeout_seconds())
    try:
        response = client.messages.create(**request)
    except anthropic.AuthenticationError:
        raise ProviderError("The API key was rejected (401). Check ANTHROPIC_API_KEY.")
    except anthropic.PermissionDeniedError as e:
        raise ProviderError(f"The key is not allowed to use this model or feature (403): {e.message}")
    except anthropic.NotFoundError as e:
        raise ProviderError(f"Model '{request['model']}' was not found (404). "
                            f"Check LEARNING_DESK_MODEL. Details: {e.message}")
    except anthropic.RateLimitError as e:
        raise ProviderError(f"Rate limited (429). Wait and try again. Details: {e.message}")
    except anthropic.BadRequestError as e:
        raise ProviderError(f"The provider rejected the request (400): {e.message}")
    except anthropic.APIStatusError as e:
        raise ProviderError(f"Provider error ({e.status_code}): {e.message}")
    except anthropic.APITimeoutError:
        raise ProviderError(f"No response within {config.timeout_seconds():.0f} seconds. Nothing was saved from this attempt.")
    except anthropic.APIConnectionError:
        raise ProviderError("Could not reach the provider. Check your internet connection.")

    raw = response.model_dump_json(indent=2)
    usage = response.usage.model_dump(exclude_none=True) if response.usage else None
    meta = {"raw": raw, "returned_model": response.model, "stop_reason": response.stop_reason, "usage": usage}

    if response.stop_reason == "refusal":
        category = getattr(response.stop_details, "category", None) if response.stop_details else None
        raise ProviderError(f"The model declined this request (refusal, category: {category}).", **meta)
    if response.stop_reason == "max_tokens":
        raise ProviderError("The response was cut off at the token limit, so it is incomplete. "
                            "Raise LEARNING_DESK_MAX_TOKENS or shorten the session.", **meta)

    text = "".join(block.text for block in response.content if block.type == "text")
    return ProviderResponse(text=text, **meta)


def redact(request: dict) -> str:
    """JSON for the 'Inspect AI call' panel. build_request() never includes credentials,
    so this is a plain dump; it exists so there is one obvious place to add redaction."""
    return json.dumps(request, indent=2, ensure_ascii=False)
