from pathlib import Path
import runpy
import sys

TARGET = Path(__file__).resolve().parents[1] / "run.py"


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"Could not find consolidated app entrypoint: {TARGET}")
    sys.path.insert(0, str(TARGET.parent))
    runpy.run_path(str(TARGET), run_name="__main__")


if __name__ == "__main__":
    main()
