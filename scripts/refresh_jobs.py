#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
jobs_path = ROOT /  "jobs.json"
updated_path = ROOT /  "last-updated.json"

now = datetime.now(timezone.utc)
today = now.date().isoformat()

with jobs_path.open("r", encoding="utf-8") as f:
    records = json.load(f)

active = []
expired = 0
for job in records:
    deadline = str(job.get("deadline", "")).strip()
    if deadline and deadline < today:
        expired += 1
        continue
    job["lastVerified"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    active.append(job)

active.sort(key=lambda x: (str(x.get("posted", "")), str(x.get("deadline", ""))), reverse=True)

with jobs_path.open("w", encoding="utf-8") as f:
    json.dump(active, f, ensure_ascii=False, indent=2)
    f.write("\n")

metadata = {
    "updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "activeJobs": len(active),
    "expiredRemoved": expired,
    "automation": "GitHub Actions",
    "refreshInterval": "Every 6 hours"
}
with updated_path.open("w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Active jobs: {len(active)} | expired removed: {expired}")
