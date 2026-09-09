"""Translation via Google's unofficial batchexecute endpoint (no API key).

Also undocumented, and the response is a length-delimited envelope rather than
plain JSON. It is here because it is rate limited far less readily than the
single endpoint, which makes it a good last resort.
"""

import json

from translation._http import HttpTranslator, raise_for_rate_limit

_ENDPOINT = "https://translate.google.com/_/TranslateWebserverUi/data/batchexecute"
_RPC_ID = "MkEWBc"


class GoogleBatchTranslator(HttpTranslator):
    """Rate limited less readily than the single endpoint, slightly less accurate."""

    name = "batchexecute (unofficial)"

    def _translate_chunk(self, chunk: str) -> str:
        inner = json.dumps([[chunk, self._src, self._dst, True], [None]],
                           ensure_ascii=False)
        freq = json.dumps([[[_RPC_ID, inner, None, "generic"]]], ensure_ascii=False)

        response = self._session.post(
            _ENDPOINT, data={"f.req": freq}, timeout=self._timeout
        )
        raise_for_rate_limit(response)
        return self._parse(response.text)

    @staticmethod
    def _parse(raw: str) -> str:
        """Extract the translation from the batchexecute envelope.

        The shape is undocumented, so any structural surprise becomes an
        ordinary provider failure and the chain falls through.
        """
        try:
            # The body opens with a )]}' anti-JSON prefix and interleaves length
            # markers with payload lines.
            for line in raw.splitlines():
                line = line.strip()
                if not line.startswith("[["):
                    continue
                outer = json.loads(line)
                payload = json.loads(outer[0][2])
                segments = payload[1][0][0][5]
                return "".join(seg[0] for seg in segments if seg and seg[0])
        except Exception as e:
            raise RuntimeError(f"unexpected batchexecute response: {e}") from e

        raise RuntimeError("no translation found in batchexecute response")
