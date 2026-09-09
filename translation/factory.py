"""Translation provider factory.

Providers are tried in order, so the app works with no setup at all and
silently upgrades to the official API once a key is present.
"""

from typing import Optional

from config import (
    GOOGLE_TRANSLATE_API_KEY,
    TRANSLATION_CONNECT_TIMEOUT,
    TRANSLATION_ENABLED,
    TRANSLATION_MAX_CHUNK_CHARS,
    TRANSLATION_PROVIDER,
    TRANSLATION_RETRIES,
    TRANSLATION_SOURCE_LANG,
    TRANSLATION_TARGET_LANG,
    TRANSLATION_TIMEOUT,
)
from translation.provider import TranslationProvider


class FallbackTranslator(TranslationProvider):
    """Tries each provider in order until one answers.

    Stays quiet on failure, unlike ai.FallbackProvider: this runs once per
    transcript line, so a warning per failure would flood the view. The
    pipeline's circuit breaker is what surfaces a sustained outage.
    """

    def __init__(self, providers: list[TranslationProvider]) -> None:
        if not providers:
            raise ValueError("FallbackTranslator needs at least one provider")
        self._providers = providers
        self.name = " -> ".join(p.name for p in providers)

    def translate(self, text: str) -> str:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                return provider.translate(text)
            except Exception as e:
                last_error = e
        raise last_error


def _cloud() -> Optional[TranslationProvider]:
    """The official API, or None when no key is configured."""
    if not GOOGLE_TRANSLATE_API_KEY:
        return None
    from translation.google_cloud import GoogleCloudTranslator
    return GoogleCloudTranslator(
        api_key=GOOGLE_TRANSLATE_API_KEY,
        source_lang=TRANSLATION_SOURCE_LANG,
        target_lang=TRANSLATION_TARGET_LANG,
        timeout=TRANSLATION_TIMEOUT,
        connect_timeout=TRANSLATION_CONNECT_TIMEOUT,
        max_chunk_chars=TRANSLATION_MAX_CHUNK_CHARS,
    )


def _single() -> TranslationProvider:
    from translation.google_single import GoogleSingleTranslator
    return GoogleSingleTranslator(
        source_lang=TRANSLATION_SOURCE_LANG,
        target_lang=TRANSLATION_TARGET_LANG,
        timeout=TRANSLATION_TIMEOUT,
        connect_timeout=TRANSLATION_CONNECT_TIMEOUT,
        max_chunk_chars=TRANSLATION_MAX_CHUNK_CHARS,
        retries=TRANSLATION_RETRIES,
    )


def _batch() -> TranslationProvider:
    from translation.google_batch import GoogleBatchTranslator
    return GoogleBatchTranslator(
        source_lang=TRANSLATION_SOURCE_LANG,
        target_lang=TRANSLATION_TARGET_LANG,
        timeout=TRANSLATION_TIMEOUT,
        connect_timeout=TRANSLATION_CONNECT_TIMEOUT,
        max_chunk_chars=TRANSLATION_MAX_CHUNK_CHARS,
    )


def _build() -> Optional[TranslationProvider]:
    provider = TRANSLATION_PROVIDER.strip().lower()

    if provider == "cloud":
        return _cloud()
    if provider == "single":
        return _single()
    if provider == "batch":
        return _batch()

    # "auto": official API when a key exists, then the unofficial endpoints so
    # the app still works with no setup. The batch endpoint is last because it
    # is rate limited less readily than the single one.
    chain = [p for p in (_cloud(), _single(), _batch()) if p is not None]
    return FallbackTranslator(chain)


def get_translator() -> Optional[TranslationProvider]:
    """Get the configured translator, or None when translation is off.

    None puts the pipeline in passthrough mode, so the disabled path behaves
    exactly as the app did before translation existed.
    """
    if not TRANSLATION_ENABLED or TRANSLATION_PROVIDER.strip().lower() == "off":
        return None
    try:
        return _build()
    except Exception:
        return None


def describe_translator(translator: Optional[TranslationProvider] = None) -> str:
    """Describe the active configuration for the startup panel."""
    if translator is None:
        return "set TRANSLATION_ENABLED=true to turn it on"
    return f"{TRANSLATION_SOURCE_LANG} -> {TRANSLATION_TARGET_LANG} via {translator.name}"
