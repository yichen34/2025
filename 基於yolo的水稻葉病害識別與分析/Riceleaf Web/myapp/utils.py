from pathlib import Path
from functools import lru_cache
import json
from typing import Any, Dict, List, Optional
from django.conf import settings

# 依你的實際 app 名稱調整這段路徑
DATA_PATH = Path(settings.BASE_DIR) / "data" / "disease_guides.json"

@lru_cache(maxsize=1)
def load_guides() -> Dict[str, Dict[str, Any]]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _match_guide(guides: Dict[str, Dict[str, Any]], label: str) -> Optional[Dict[str, Any]]:
    if not label:
        return None
    if label in guides:
        return guides[label]
    cands = {label, label.strip(), label.lower(), label.title(), label.replace(" ", ""), label.replace("_", "")}
    for k, v in guides.items():
        keys = {k, k.lower(), k.replace(" ", ""), k.replace("_", "")}
        if cands & keys:
            return v
        aliases = v.get("aliases", [])
        aliases_norm = set()
        for a in aliases:
            aliases_norm |= {a, a.lower(), a.replace(" ", ""), a.replace("_", "")}
        if cands & aliases_norm:
            return v
    return None

def attach_guides_to_results(detected_classes: List[str]) -> List[Dict[str, Any]]:
    guides = load_guides()
    enriched = []
    for cls in detected_classes:
        guide = _match_guide(guides, cls)
        enriched.append({
            "label": cls,
            "display_name": (guide or {}).get("display_name", cls),
            "solutions": (guide or {}).get("solutions", []),
            "prevention": (guide or {}).get("prevention", [])
        })
    return enriched
