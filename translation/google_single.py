"""Translation via Google's unofficial single-translate endpoint (no API key).

Undocumented and unsupported: it is the backend translate.google.com calls, not
a published API. Used as a no-setup fallback when no Cloud Translation key is
configured. Its known failure mode is rate limiting, not network errors.
"""

import random
import time

from translation._http import HttpTranslator, RateLimited, raise_for_rate_limit

_ENDPOINT = "https://translate.googleapis.com/translate_a/single"


class GoogleSingleTranslator(HttpTranslator):
    """More accurate than the batch endpoint, but rate limited sooner."""

    name = "translate_a/single (unofficial)"

    def __init__(self, *args, retries: int = 1, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._retries = retries

    def _translate_chunk(self, chunk: str) -> str:
        last_error: Exception | None = None

        for attempt in range(self._retries + 1):
            try:
                response = self._session.post(
                    _ENDPOINT,
                    data={
                        "client": "gtx",
                        "sl": self._src,
                        "tl": self._dst,
                        "dt": "t",
                        "q": chunk,
                    },
                    timeout=self._timeout,
                )
                raise_for_rate_limit(response)
                return self._parse(response.json())
            except RateLimited:
                # Never retry a rate limit: the segment's hold expires anyway and
                # retrying only deepens the limit. Let the chain move on.
                raise
            except Exception as e:
                last_error = e
                if attempt < self._retries:
                    # Backoff with jitter, for genuine network errors only.
                    time.sleep(0.3 * (3 ** attempt) + random.uniform(0, 0.2))

        raise last_error if last_error else RuntimeError("translation failed")

    @staticmethod
    def _parse(payload: object) -> str:
        """Pull the text out of the endpoint's nested-array response."""
        try:
            segments = payload[0]
        except (TypeError, IndexError, KeyError):
            return ""
        if not segments:
            return ""
        return "".join(seg[0] for seg in segments if seg and seg[0])
