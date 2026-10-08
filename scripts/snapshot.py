"""Save a daily snapshot of public GitHub stats for OpenTeams open-source repos.

GitHub only reports the current release download total, not its history, so
running this daily builds the history needed for growth-over-time charts.
"""

import base64
import csv
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPOS = [
    "nebari-dev/nebi",
    "nebari-dev/nebari-infrastructure-core",
    "nebari-dev/nebari",
    "artifact-keeper/artifact-keeper",
]

# The dashboard's list of first-party software packs; read at runtime so new packs are picked up.
TRACKED_PACKS_PATH = "/repos/nebari-dev/software-pack-dashboard/contents/tracked-packs.yaml"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
API = "https://api.github.com"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get(path):
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def release_downloads(repo):
    total, page = 0, 1
    while releases := get(f"/repos/{repo}/releases?per_page=100&page={page}"):
        total += sum(asset["download_count"] for r in releases for asset in r["assets"])
        page += 1
    return total


def software_pack_repos():
    content = base64.b64decode(get(TRACKED_PACKS_PATH)["content"]).decode()
    return [line.split("repo:")[1].strip() for line in content.splitlines() if "repo:" in line]


def repo_stats_row(repo, group):
    info = get(f"/repos/{repo}")
    return {
        "date": TODAY,
        "repo": repo,
        "group": group,
        "stars": info["stargazers_count"],
        "forks": info["forks_count"],
        "release_downloads": release_downloads(repo),
    }


def merge_into_csv(filename, new_rows, key_fields):
    """Newer rows replace older rows with the same key, so re-runs on the same day don't duplicate."""
    if not new_rows:
        return
    path = DATA_DIR / filename
    rows = {}
    if path.exists():
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                rows[tuple(row[k] for k in key_fields)] = row
    for row in new_rows:
        rows[tuple(str(row[k]) for k in key_fields)] = row
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(new_rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows.values(), key=lambda r: tuple(str(r[k]) for k in key_fields)))


def main():
    DATA_DIR.mkdir(exist_ok=True)
    rows = [repo_stats_row(repo, "core") for repo in REPOS]
    rows += [repo_stats_row(repo, "software-pack") for repo in software_pack_repos()]
    merge_into_csv("repo_stats.csv", rows, ["date", "repo"])


if __name__ == "__main__":
    main()
