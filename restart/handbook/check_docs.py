"""Check local handbook links and that the source plan is bounded and pinned."""
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parent
checked = 0
for path in (root.parent).rglob("*.md"):
    content = path.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", content):
        if "://" in target or target.startswith("#"):
            continue
        target = target.split("#", 1)[0].strip("<>")
        if target and not (path.parent / target).exists():
            raise ValueError(f"Broken local link: {path}: {target}")
    checked += 1
plan = json.loads((root / "sources.lock.json").read_text(encoding="utf-8"))
source = plan["real_dataset"]
assert re.fullmatch(r"[0-9a-f]{40}", source["revision"])
assert sum(item["bytes"] for item in source["files"]) <= source["download_budget_bytes"] <= 7000000
assert all(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in source["files"])
assert all(not item["path"].startswith("videos/") for item in source["files"])
print(f"{checked} Markdown documents: local links and pinned bounded download plan OK")
