"""Self-contained offline atlas player, with the desktop v1 frame timing."""
from __future__ import annotations
import base64
from importlib.resources import files
import json
from pathlib import Path
from .project import child, config, current_build
from .engine import STATES, DURATIONS_MS

LABELS = dict(zip([s[0] for s in STATES], ['待机','向右跑','向左跑','挥手','跳跃','挫败','等候','工作','检查成果']))

HTML = files("codex_various_pet").joinpath("data/player.html").read_text(encoding="utf-8")

def render(root: Path) -> Path:
    atlas, quality = current_build(root)
    payload = {
        'displayName': config(root)['display_name'],
        'imageBase64': base64.b64encode(atlas.read_bytes()).decode('ascii'),
        'atlasPath': 'final/spritesheet-v1.png',
        'qualityPath': 'final/quality.json',
        'sha256': quality['output_sha256'],
        'quality': quality,
        'states': [dict(name=name,label=LABELS[name],count=count,row=row,durations=DURATIONS_MS[name]) for row,(name,count) in enumerate(STATES)],
    }
    encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    output=child(root,'preview/pet-preview.html')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(HTML.replace('__DATA__',encoded),encoding='utf-8')
    return output
