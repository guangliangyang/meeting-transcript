"""Translation via the official Cloud Translation API v2.

The supported path: documented, quota'd and covered by Google's API terms. Free
for the first 500k characters per month, then billed per character. Used
whenever GOOGLE_TRANSLATE_API_KEY is set.
"""

from translation._http import HttpTranslator, raise_for_rate_limit

_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"


class GoogleCloudTranslator(HttpTranslator):
    """Official API. Needs a key from a billing-enabled GCP project."""

    name = "Cloud Translation (official)"

    def __init__(self, api_key: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._api_key = api_key

    def _translate_chunk(self, chunk: str) -> str:
        response = self._session.post(
            _ENDPOINT,
            params={"key": self._api_key},
            data={
                "q": chunk,
                "source": self._src,
                "target": self._dst,
                # Without this the API defaults to "html" and returns escaped
                # entities like &#39;, which would show up literally.
                "format": "text",
            },
            timeout=self._timeout,
        )
        raise_for_rate_limit(response)
        return self._parse(response.json())

    @staticmethod
    def _parse(payload: object) -> str:
        try:
            return payload["data"]["translations"][0]["translatedText"]
        except (TypeError, KeyError, IndexError) as e:
            raise RuntimeError(f"unexpected Cloud Translation response: {e}") from e
