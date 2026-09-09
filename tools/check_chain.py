"""Check the translation provider chain falls through correctly.

The chain is what replaces the old Gemini fallback, so its failure behaviour
needs to be proven rather than assumed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation._http import RateLimited  # noqa: E402
from translation.factory import FallbackTranslator  # noqa: E402
from translation.provider import TranslationProvider  # noqa: E402

results = []


def check(name, condition, detail=""):
    results.append(bool(condition))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


class Fake(TranslationProvider):
    def __init__(self, name, answer=None, error=None):
        self.name = name
        self._answer, self._error = answer, error
        self.calls = 0

    def translate(self, text):
        self.calls += 1
        if self._error:
            raise self._error
        return self._answer


def main():
    # 1. first provider answers, later ones are never called
    a = Fake("A", answer="from-A")
    b = Fake("B", answer="from-B")
    chain = FallbackTranslator([a, b])
    out = chain.translate("x")
    check("first provider wins", out == "from-A" and b.calls == 0, f"got {out!r}")

    # 2. first fails -> second answers
    a = Fake("A", error=RuntimeError("cloud down"))
    b = Fake("B", answer="from-B")
    out = FallbackTranslator([a, b]).translate("x")
    check("falls through on error", out == "from-B", f"got {out!r}")

    # 3. rate limit on both unofficial stages -> third answers
    a = Fake("cloud", error=RuntimeError("no key"))
    b = Fake("single", error=RateLimited("HTTP 429"))
    c = Fake("batch", answer="from-batch")
    out = FallbackTranslator([a, b, c]).translate("x")
    check("429 falls through to batch", out == "from-batch" and c.calls == 1, f"got {out!r}")

    # 4. all fail -> raises (pipeline turns this into an untranslated line)
    try:
        FallbackTranslator([Fake("A", error=RateLimited("429")),
                            Fake("B", error=RuntimeError("boom"))]).translate("x")
        check("all-fail raises", False)
    except Exception as e:
        check("all-fail raises", True, f"{type(e).__name__}: {e}")

    # 5. chain name reports the real composition
    chain = FallbackTranslator([Fake("one"), Fake("two")])
    check("chain names itself", chain.name == "one -> two", chain.name)

    # 6. bad key: the real cloud provider must fail, not hang or crash the app
    from translation.google_cloud import GoogleCloudTranslator
    from translation.google_single import GoogleSingleTranslator
    bad = GoogleCloudTranslator(api_key="definitely-not-a-valid-key")
    try:
        bad.translate("The build is broken.")
        check("bad key rejected", False, "unexpectedly succeeded")
    except Exception as e:
        check("bad key rejected", True, type(e).__name__)

    # 7. and the chain recovers from it against the live endpoint
    out = FallbackTranslator([bad, GoogleSingleTranslator()]).translate("The build is broken.")
    check("bad key falls through to live single", bool(out) and out != "", repr(out))

    print(f"\n{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
