from __future__ import annotations

import re

import requests

from src.ai.advisory import DISCLAIMER


class NIMServiceError(RuntimeError):
    """Raised when a NIM rewrite is unavailable or fails safety verification."""


def rewrite_advisory(draft: str, location: str, score: int, *, api_key: str,
                     base_url: str, model: str, timeout: int = 30) -> str:
    if not api_key or not model:
        raise NIMServiceError("NVIDIA NIM is not configured.")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Rewrite flood planning advisories in calm, plain language. Preserve every fact, "
                    "number, risk level, action, uncertainty statement, and disclaimer. Never add claims, "
                    "predictions, emergency instructions, or new evidence. Return only the rewritten advisory."
                ),
            },
            {"role": "user", "content": draft},
        ],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 500,
        "stream": False,
    }
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        raise NIMServiceError("The AI rewrite is currently unavailable.") from exc

    risk_label_match = re.search(r"Indicative disruption risk: (Low|Moderate|High)", draft)
    numbers = set(re.findall(r"\d+(?:\.\d+)?", draft))
    required_text = (location, f"{score}/100", DISCLAIMER,
                     risk_label_match.group(1) if risk_label_match else "")
    if not content or len(content) > 3_000 or any(value not in content for value in required_text):
        raise NIMServiceError("The AI rewrite did not preserve the verified advisory facts.")
    if any(number not in content for number in numbers):
        raise NIMServiceError("The AI rewrite changed or omitted a verified number.")
    return content
