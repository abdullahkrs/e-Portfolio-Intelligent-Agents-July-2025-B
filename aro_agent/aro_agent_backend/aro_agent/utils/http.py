from __future__ import annotations
import time, random
import requests
from typing import Optional, Dict, Any, Tuple

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

def http_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
    retries: int = 5,
    backoff_base: float = 0.8,
    max_sleep: float = 10.0,
) -> Tuple[int, str, Dict[str, str]]:
    """
    GET with retry on 429/5xx. Honors Retry-After (seconds) when present.
    Exponential backoff with jitter. Returns (status_code, text, response_headers)
    """
    last_exc = None
    session = requests.Session()

    for attempt in range(retries):
        try:
            r = session.get(url, params=params, headers=headers, timeout=timeout)
            status = r.status_code

            # Success
            if status < 400:
                return status, r.text, dict(r.headers)

            # Retry on rate-limit/server errors
            if status in RETRYABLE_STATUS:
                retry_after = 0.0
                ra = r.headers.get("Retry-After")
                if ra:
                    try:
                        retry_after = float(ra)
                    except ValueError:
                        retry_after = 0.0
                sleep_s = min((backoff_base ** attempt) * 1.5 + random.uniform(0, 0.5), max_sleep)
                time.sleep(max(retry_after, sleep_s))
                continue

            # Non-retryable: return as-is
            return status, r.text, dict(r.headers)

        except requests.RequestException as e:
            last_exc = e
            sleep_s = min((backoff_base ** attempt) * 1.5 + random.uniform(0, 0.5), max_sleep)
            time.sleep(sleep_s)

    if last_exc:
        raise last_exc
    raise RuntimeError(f"Exceeded retries for {url}")
