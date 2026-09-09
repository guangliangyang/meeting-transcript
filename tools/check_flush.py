"""Check the Live Captions flush bookkeeping. No network, no audio, no pywinauto.

The risk in the flush rework is _last_output_position: advance it too far and
the tail of a sentence is dropped, too little and text is emitted twice. One
invariant catches both.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import threading  # noqa: E402

from transcription.windows import WindowsTranscriber  # noqa: E402
from translation._http import split_chunks  # noqa: E402

TS = re.compile(r'^\[\d{2}:\d{2}:\d{2}\]\s*')


def new_transcriber():
    """Build one without running __init__, which requires pywinauto."""
    t = WindowsTranscriber.__new__(WindowsTranscriber)
    t._transcript_parts = []
    t._lock = threading.Lock()
    t._output_lock = threading.Lock()
    t._full_transcript = ""
    t._last_seen_text = ""
    t._last_output_position = 0
    t._output_min_chars = 25
    t._output_max_words = 40
    t.emitted = []
    t.on_transcript = t.emitted.append
    return t


def norm(s):
    return " ".join(s.split())


def check(name, chunks, flush_all_at_end=True):
    t = new_transcriber()
    positions = []

    for chunk in chunks:
        t._full_transcript += " " + chunk
        pending = t._full_transcript[t._last_output_position:]
        cut = t._find_flush_boundary(pending)
        if cut and len(pending.strip()) >= t._output_min_chars:
            t._output_from_buffer(limit=cut)
            positions.append(t._last_output_position)

    if flush_all_at_end:
        t._output_from_buffer()
        positions.append(t._last_output_position)

    emitted = norm(" ".join(TS.sub('', e) for e in t.emitted))
    consumed = norm(t._full_transcript[:t._last_output_position])

    ok_content = emitted == consumed
    ok_monotonic = positions == sorted(positions)
    ok_bounds = t._last_output_position <= len(t._full_transcript)

    status = "PASS" if (ok_content and ok_monotonic and ok_bounds) else "FAIL"
    print(f"[{status}] {name}  ({len(t.emitted)} emitted)")
    if not ok_content:
        print(f"    emitted : {emitted[:160]!r}")
        print(f"    consumed: {consumed[:160]!r}")
    if not ok_monotonic:
        print(f"    positions not monotonic: {positions}")
    if not ok_bounds:
        print("    position past end of buffer")
    return status == "PASS"


def main():
    results = []

    results.append(check("plain sentences", [
        "Good morning everyone.", "The build is broken again.",
        "We should fix it before standup.",
    ]))
    results.append(check("no punctuation at all", [
        "so i think we keep polling until the window shows up and then we read "
        "whatever the longest text node happens to be at that moment which is "
        "usually the caption text but not always and that is the tricky part "
        "here honestly",
    ]))
    results.append(check("terminator mid-chunk", [
        "First part is done. Second part is still",
        "in progress and will land later.",
    ]))
    results.append(check("short noise fragments", ["ok", "um", "a.", "right."]))
    results.append(check("quoted terminator", [
        'He said "ship it." Then he left the call.',
    ]))
    results.append(check("no trailing flush", [
        "One complete sentence here. And a dangling fragment",
    ], flush_all_at_end=False))

    # limit larger than the buffer must clamp, not overrun
    t = new_transcriber()
    t._full_transcript = " Short buffer."
    t._output_from_buffer(limit=10_000)
    ok = t._last_output_position == len(t._full_transcript)
    print(f"[{'PASS' if ok else 'FAIL'}] limit beyond buffer end clamps")
    results.append(ok)

    # chunking never exceeds the configured limit
    corpus = ("We need to bump the datastore version before the release. " * 30
              + "x" * 900)
    chunks = split_chunks(corpus, 200)
    ok = bool(chunks) and all(len(c) <= 200 for c in chunks)
    print(f"[{'PASS' if ok else 'FAIL'}] chunks within limit "
          f"({len(chunks)} chunks, max {max(len(c) for c in chunks)})")
    results.append(ok)

    print()
    print(f"{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
