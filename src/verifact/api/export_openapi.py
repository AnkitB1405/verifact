"""Write the OpenAPI document to a file.

Owner: P1. CI runs this and publishes the result as an artifact; P2 generates
the dashboard's request shapes from it rather than hand-writing them, so the UI
cannot describe an endpoint that does not exist.

    python -m verifact.api.export_openapi build/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    target = Path(args[0]) if args else Path("build/openapi.json")
    # Importing the app is what validates that every route and schema is
    # constructible, so a broken route fails this step rather than at runtime.
    from verifact.api.app import app

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    paths = len(app.openapi().get("paths", {}))
    print(f"wrote {target} ({paths} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
