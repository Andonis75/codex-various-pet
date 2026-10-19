"""Run the bundled various-pet tool without depending on an editable checkout."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from codex_various_pet.cli import main
except ModuleNotFoundError as error:
    if error.name in {"PIL", "numpy"}:
        raise SystemExit("Install the runner dependencies with this Python: python -m pip install 'Pillow>=12.3' 'numpy>=1.26'") from error
    raise

raise SystemExit(main())
