"""Versioned production heuristics, not measured learning or retention scores."""

POLICY_VERSION = "prediction-retrieval-1"
PAUSE_SECONDS = {"prediction": 2.0, "retrieval": 3.0}


def pause_after(board, segment_id):
    return next(
        (
            PAUSE_SECONDS.get(b.kind, 0.0)
            for b in board.teaching_beats
            if b.segment_id == segment_id
        ),
        0.0,
    )


def timed_teaching_beats(board, segments):
    """Use measured speech, including actual silence inserted into the audio track."""
    by_id = {s["id"]: s for s in segments}
    return [
        {
            "kind": b.kind,
            "text": b.text,
            "start": by_id[b.segment_id]["start"],
            "speech_end": by_id[b.segment_id]["end"],
            "end": by_id[b.segment_id]["end"] + pause_after(board, b.segment_id),
        }
        for b in board.teaching_beats
    ]


def timing_issues(beats):
    """Fail closed on an unusable opening; thresholds are tunable product choices."""
    issues = []
    if not beats:
        return ["Missing measured teaching beats"]
    if beats[0]["speech_end"] > 3.5:
        issues.append("Shorten the hook to finish within 3.5 seconds of measured speech")
    if beats[1]["speech_end"] > 9.0:
        issues.append("Finish asking the prediction within 9 seconds; keep it concise")
    return issues
