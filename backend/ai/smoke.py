"""Opt-in real-model check: python -m backend.ai.smoke (never downloads models)."""

import json
from time import perf_counter

from pydantic import ValidationError

from backend.ai import AIError, create_provider


SAMPLES = [
    "Four people want bowling and dinner under $60 each.",
    "Six friends want competitive activities followed by cocktails.",
    "A couple wants an affordable outdoor date.",
    "A group wants to watch a baseball game on 2026-11-07.",
]


def main() -> int:
    try:
        provider = create_provider()
        for text in SAMPLES:
            started = perf_counter()
            result = provider.interpret(text)
            print(json.dumps({"request": text, "seconds": round(perf_counter() - started, 2),
                              "response": result.model_dump(mode="json")}))
    except (AIError, ValidationError) as error:
        print(f"AI smoke check failed: {error}")
        return 1
    print("Communication and schema checks passed. Review values for accuracy; schema validity alone is insufficient.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
