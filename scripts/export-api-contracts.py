"""Export API-owned schemas from runtime models; --check detects stale artifacts."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))

from app.core.config import Settings  # noqa: E402
from app.core.migrate import definitions  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.quizzes.schemas import (  # noqa: E402
    AnswerRequest,
    AnswerResponse,
    QuizCard,
    RecoveryRequest,
    RecoveryResponse,
)
from app.modules.recommendations.responses import FeedResponse  # noqa: E402
from app.modules.recommendations.schemas import (  # noqa: E402
    EventResponse,
    GateRequest,
    GateResponse,
    SessionRequest,
    SessionResponse,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    models = [
        FeedResponse,
        SessionRequest,
        SessionResponse,
        GateRequest,
        GateResponse,
        EventResponse,
        QuizCard,
        AnswerRequest,
        AnswerResponse,
        RecoveryRequest,
        RecoveryResponse,
    ]
    output = {
        ROOT
        / "contracts/schemas/feed"
        / f"{model.__name__}.schema.json": model.model_json_schema()
        for model in models
    }
    app = create_app(
        settings=Settings(
            environment="test", persistence="fixture_sqlite", _env_file=None
        )
    )
    output[ROOT / "contracts/schemas/feed/openapi.json"] = app.openapi()
    output[ROOT / "database/domains/learning/api-runtime-v1.json"] = definitions()
    stale = []
    for path, value in output.items():
        serialized = json.dumps(value, indent=2, sort_keys=True) + "\n"
        if args.check:
            if not path.exists() or path.read_text() != serialized:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(serialized)
    if stale:
        raise SystemExit("Outdated API schema artifacts: " + ", ".join(stale))
    print(
        f"{'Verified' if args.check else 'Exported'} {len(output)} API-owned schema artifacts"
    )


if __name__ == "__main__":
    main()
