"""File-only Academic Setup preparation. There is deliberately no execution option."""
import argparse
import json

from .inputs import load_plan
from .policy import EXPECTED_IMAGE, LOCAL_ENDPOINT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    plan = load_plan()
    print(json.dumps({
        "preparation": "PASS",
        "execution_authorized": False,
        "endpoint": LOCAL_ENDPOINT,
        "image_reference": EXPECTED_IMAGE,
        "platform": "linux/amd64",
        "preceding_migrations": 45,
        "academic_migrations": [item.path for item in plan.migrations[45:]],
        "pinned_inputs": len(plan.inputs),
        "execution_blockers": [
            "Full approved image ID absent: supplied 'sha256' is incomplete",
            "Engine ID, executable path/hash and client/server versions need verification",
            "Complete image Config and bootstrap command fingerprints need review",
            "PostgreSQL exec/PID 1 UID/GID, binaries and extension versions need verification",
            "Fixture/probe review and explicit container/database execution approval required",
            "Live transport is disabled; preparation CLI has no execution option",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
