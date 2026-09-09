"""Shared HTTP plumbing for the translation providers."""

import re
from abc import abstractmethod
from collections import OrderedDict

import requests

from translation.provider import TranslationProvider

# The bare python-requests user agent gets intermittent 403s from the
# unofficial endpoints.
USER_AGENT = "Mozilla/5.0"

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')


class RateLimited(Exception):
    """The endpoint refused us for quota reasons rather than a real error.

    Kept distinct from network failures because the right response differs:
    retrying a rate limit immediately makes it worse, so the chain should move
    on to the next provider instead.
    """


def make_session() -> requests.Session:
    """A session per provider - reusing it skips the TLS handshake per call.

    Sessions are not documented thread-safe, so each provider instance owns one
    and TRANSLATION_WORKERS defaults to 1.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def raise_for_rate_limit(response: requests.Response) -> None:
    """Turn a quota refusal into RateLimited, anything else into an HTTPError."""
    if response.status_code in (429, 403):
        raise RateLimited(f"HTTP {response.status_code} from {response.url}")
    response.raise_for_status()


def split_chunks(text: str, limit: int) -> list[str]:
    """Split oversized text on sentence boundaries.

    A safety net, not a routine path: the endpoints handle several thousand
    characters per request and chunks are translated sequentially, so a low
    limit costs latency. Transcript segments normally return a single chunk.
    """
    chunks: list[str] = []
    current = ""

    for sentence in _SENTENCE_SPLIT.split(text):
        if not sentence:
            continue
        while len(sentence) > limit:
            # A single sentence over the limit: cut at the last space that
            # fits, or hard-cut when there is no space at all.
            cut = sentence.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].lstrip()
        if not current:
            current = sentence
        elif len(current) + 1 + len(sentence) <= limit:
            current = f"{current} {sentence}"
        else:
            chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)
    return chunks


class BoundedCache:
    """Tiny LRU. Live Captions' sliding window can re-emit near-identical text.

    Bounded so a long meeting cannot grow it without limit.
    """

    def __init__(self, max_entries: int = 256) -> None:
        self._max = max_entries
        self._data: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> str | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: str) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self._max:
            self._data.popitem(last=False)


class HttpTranslator(TranslationProvider):
    """Shared shape for the HTTP-backed providers.

    They differ only in how one chunk is sent and parsed, so everything else -
    trimming, caching, chunking and joining - lives here.
    """

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "zh-CN",
        timeout: float = 3.0,
        connect_timeout: float = 2.0,
        max_chunk_chars: int = 4000,
    ) -> None:
        self._src = source_lang
        self._dst = target_lang
        # Tuple, not a scalar: a DNS/connect hang on a dropped VPN is the common
        # offline failure and needs its own shorter bound.
        self._timeout = (connect_timeout, timeout)
        self._max_chunk_chars = max_chunk_chars
        self._session = make_session()
        self._cache = BoundedCache()

    def translate(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""

        cached = self._cache.get(text)
        if cached is not None:
            return cached

        # Join on "" - Chinese has no inter-word spaces.
        result = "".join(
            self._translate_chunk(c)
            for c in split_chunks(text, self._max_chunk_chars)
        )
        self._cache.put(text, result)
        return result

    @abstractmethod
    def _translate_chunk(self, chunk: str) -> str:
        """Translate one chunk that is known to fit in a single request."""
