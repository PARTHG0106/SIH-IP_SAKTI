"""Registry / form router — turns a classified question into official action links."""
from __future__ import annotations
import yaml
from .config import settings

# default registry regimes to surface per classifier category
CATEGORY_REGIMES = {
    "classical": ["drug", "patent"],
    "proprietary": ["drug", "patent", "trademark"],
    "new_drug": ["drug", "patent", "biodiversity"],
    "phytopharmaceutical": ["drug", "patent", "biodiversity"],
    "ayurveda_aahar": ["food", "trademark"],
    "cosmetic": ["trademark", "design"],
}


class RegistryRouter:
    def __init__(self, path=None):
        with open(path or settings.registry_path, encoding="utf-8") as f:
            self.registries = yaml.safe_load(f)["registries"]

    def get(self, resource_id: str):
        return next((r for r in self.registries if r["id"] == resource_id), None)

    def route(self, jurisdiction: str, regimes: set[str] | None = None,
              category: str | None = None, limit: int = 12) -> list[dict]:
        regimes = set(regimes or set())
        if category:
            regimes |= set(CATEGORY_REGIMES.get(category, []))
        out, seen = [], set()
        for r in self.registries:
            if r["id"] in seen:
                continue
            if r["jurisdiction"] != jurisdiction:
                continue
            if category and r.get("categories") and category not in r["categories"]:
                continue
            reg_ok = (not regimes) or (r["regime"] in regimes) or (r["regime"] == "any")
            if not reg_ok:
                continue
            out.append({
                "id": r["id"], "name": r["name"],
                "url": r["url"] if r.get("access", "free") == "free" else None,
                "regime": r["regime"],
                "jurisdiction": r["jurisdiction"], "access": r.get("access", "free"),
                "note": r.get("note"),
            })
            seen.add(r["id"])
            if len(out) >= limit:
                break
        return out
