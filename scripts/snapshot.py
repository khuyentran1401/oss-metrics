"""Save a weekly snapshot of download and star stats for OpenTeams open-source repos.

GitHub, conda-forge, Docker Hub and ghcr.io only report current totals, GitHub
only shows star dates to accounts with push access, pypistats keeps 180 days
and quay.io keeps 90, so running this weekly builds the history needed for
growth-over-time charts. Per-release downloads are rewritten in full on every run.
"""

import base64
import csv
import json
import os
import re
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

CONDA_PACKAGES = ["conda-forge/nebari", "conda-forge/nebi"]
PYPI_PACKAGES = ["nebari"]

# Docker Hub namespace -> image-name prefix to count ("" counts every image).
# quansight/qhub-* is Nebari under its pre-2022 name; it gets no new pulls.
DOCKERHUB_NAMESPACES = {"quansight": "qhub", "artifactkeeper": ""}
GHCR_ORG = "nebari-dev"
QUAY_NAMESPACE = "nebari"
# ~4,900 pulls a day for one Helm chart: an automated sync loop, not users.
QUAY_EXCLUDED = {"charts/nebari-chat"}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
API = "https://api.github.com"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def fetch_json(url, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {})) as response:
        return json.load(response)


def get(path):
    return fetch_json(
        f"{API}{path}",
        {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"},
    )


def get_all_pages(path):
    items, page = [], 1
    while batch := get(f"{path}?per_page=100&page={page}"):
        items += batch
        page += 1
    return items


def software_pack_repos():
    content = base64.b64decode(get(TRACKED_PACKS_PATH)["content"]).decode()
    return [line.split("repo:")[1].strip() for line in content.splitlines() if "repo:" in line]


def release_rows(repo):
    return [
        {
            "repo": repo,
            "tag": release["tag_name"],
            "published": (release["published_at"] or release["created_at"])[:10],
            "downloads": sum(asset["download_count"] for asset in release["assets"]),
        }
        for release in get_all_pages(f"/repos/{repo}/releases")
    ]


def repo_stats_row(repo, group, releases):
    info = get(f"/repos/{repo}")
    return {
        "date": TODAY,
        "repo": repo,
        "group": group,
        "stars": info["stargazers_count"],
        "forks": info["forks_count"],
        "release_downloads": sum(r["downloads"] for r in releases),
    }


def conda_rows():
    rows = []
    for package in CONDA_PACKAGES:
        files = fetch_json(f"https://api.anaconda.org/package/{package}")["files"]
        rows.append({"date": TODAY, "package": package, "downloads": sum(f["ndownloads"] for f in files)})
    return rows


def pypi_daily_rows():
    """Downloads per day, excluding mirrors; pypistats keeps 180 days, merging keeps the rest."""
    rows = []
    for package in PYPI_PACKAGES:
        data = fetch_json(f"https://pypistats.org/api/packages/{package}/overall?mirrors=false")["data"]
        rows += [{"date": d["date"], "package": package, "downloads": d["downloads"]} for d in data]
    return rows


def dockerhub_rows():
    rows = []
    for namespace, prefix in DOCKERHUB_NAMESPACES.items():
        images = fetch_json(f"https://hub.docker.com/v2/repositories/{namespace}/?page_size=100")["results"]
        rows += [
            {"date": TODAY, "registry": "dockerhub", "image": f"{namespace}/{image['name']}", "pulls": image["pull_count"]}
            for image in images
            if image["name"].startswith(prefix)
        ]
    return rows


def fetch_html(url):
    with urllib.request.urlopen(url) as response:
        return response.read().decode()


def ghcr_rows():
    """ghcr.io has no public API for download counts, so read them from the package pages."""
    packages_url = f"https://github.com/orgs/{GHCR_ORG}/packages"
    names, page = set(), 1
    while found := set(re.findall(rf"/orgs/{GHCR_ORG}/packages/container/package/([\w.%-]+)",
                                  fetch_html(f"{packages_url}?ecosystem=container&page={page}"))) - names:
        names |= found
        page += 1
    rows = []
    for name in sorted(names):
        count = re.search(r'Total downloads[\s\S]{0,200}?title="(\d+)"', fetch_html(f"{packages_url}/container/package/{name}"))
        rows.append({"date": TODAY, "registry": "ghcr", "image": f"{GHCR_ORG}/{name}", "pulls": int(count.group(1))})
    return rows


def quay_daily_rows():
    """Pulls per day across the namespace; quay keeps 90 days, merging keeps the rest."""
    api = "https://quay.io/api/v1/repository"
    images = [r["name"] for r in fetch_json(f"{api}?namespace={QUAY_NAMESPACE}&public=true")["repositories"]]
    per_day = {}
    for image in images:
        if image in QUAY_EXCLUDED:
            continue
        for day in fetch_json(f"{api}/{QUAY_NAMESPACE}/{image}?includeStats=true").get("stats", []):
            per_day[day["date"]] = per_day.get(day["date"], 0) + day["count"]
    # Today is still in progress, so its count would be partial.
    return [{"date": d, "pulls": n} for d, n in sorted(per_day.items()) if d < TODAY]


def write_csv(filename, rows):
    with (DATA_DIR / filename).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


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
    write_csv(filename, sorted(rows.values(), key=lambda r: tuple(str(r[k]) for k in key_fields)))


def main():
    DATA_DIR.mkdir(exist_ok=True)
    releases = {repo: release_rows(repo) for repo in REPOS}
    packs = software_pack_repos()
    pack_releases = {repo: release_rows(repo) for repo in packs}

    stats = [repo_stats_row(repo, "core", releases[repo]) for repo in REPOS]
    stats += [repo_stats_row(repo, "software-pack", pack_releases[repo]) for repo in packs]
    merge_into_csv("repo_stats.csv", stats, ["date", "repo"])
    merge_into_csv("conda_downloads.csv", conda_rows(), ["date", "package"])
    merge_into_csv("pypi_daily.csv", pypi_daily_rows(), ["date", "package"])
    merge_into_csv("container_pulls.csv", dockerhub_rows() + ghcr_rows(), ["date", "image"])
    merge_into_csv("quay_daily.csv", quay_daily_rows(), ["date"])

    write_csv("releases.csv", [row for repo in REPOS for row in releases[repo]])


if __name__ == "__main__":
    main()
