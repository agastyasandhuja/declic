import math
import re


def alignment_words(alignment, duration, offset=0, speaker="narrator"):
    if not isinstance(alignment, dict):
        raise ValueError("Missing character alignment")
    chars = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends = alignment.get("character_end_times_seconds", [])
    if not chars or not len(chars) == len(starts) == len(ends):
        raise ValueError("Mismatched alignment lengths")
    previous = 0
    for char, start, end in zip(chars, starts, ends, strict=True):
        if not isinstance(char, str) or len(char) != 1:
            raise ValueError("Alignment must contain characters")
        if not all(isinstance(t, (int, float)) and math.isfinite(t) for t in (start, end)):
            raise ValueError("Non-finite timestamps")
        if start < previous or end < start or end > duration + 0.1:
            raise ValueError("Unordered or out-of-bounds alignment")
        previous = start
    text = "".join(chars)
    return [
        {
            "text": m.group(),
            "start": offset + starts[m.start()],
            "end": offset + ends[m.end() - 1],
            "speaker": speaker,
            "char_start": m.start(),
            "char_end": m.end(),
        }
        for m in re.finditer(r"\S+", text)
    ]


def resolve_cue(cue, segment, words):
    matches = list(re.finditer(re.escape(cue.phrase), segment.spoken_text))
    if len(matches) <= cue.occurrence:
        raise ValueError("Cue cannot resolve")
    match = matches[cue.occurrence]
    overlap = [w for w in words if w["char_start"] < match.end() and w["char_end"] > match.start()]
    if not overlap:
        raise ValueError("Cue has no audible words")
    return overlap[0]["start"] if cue.edge == "start" else overlap[-1]["end"]


def caption_groups(words):
    groups, current = [], []
    for word in words:
        if current and (
            len(current) >= 5
            or sum(len(w["text"]) + 1 for w in current) + len(word["text"]) > 28
            or word["speaker"] != current[-1]["speaker"]
            or word["start"] - current[-1]["end"] > 0.35
        ):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)
    return [
        {"start": g[0]["start"], "end": g[-1]["end"], "speaker": g[0]["speaker"], "words": g}
        for g in groups
    ]


def vtt(groups):
    def stamp(t):
        ms = round(t * 1000)
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}.{ms % 1000:03}"

    return (
        "WEBVTT\n\n"
        + "\n\n".join(
            f"{stamp(g['start'])} --> {stamp(g['end'])}\n" + " ".join(w["text"] for w in g["words"])
            for g in groups
        )
        + "\n"
    )
