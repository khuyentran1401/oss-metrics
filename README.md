# oss-metrics

Daily snapshots of public GitHub stats for OpenTeams open-source repos.

## Why

GitHub only reports the current release download total, with no record of when downloads happened. Snapshotting it regularly is the only way to show download growth over time, which says more to investors than a single total.

Stars need it too: GitHub only shows when each star was given to accounts with push access to the repo. Downloads also come from conda-forge (all-time totals) and PyPI via pypistats, which only keeps 180 days of daily counts.

## Data

| File | Contents |
|---|---|
| `repo_stats.csv` | One row per repo per day: group (`core` or `software-pack`), stars, forks, release_downloads (cumulative). Sum the `software-pack` rows to report packs as one line. |
| `conda_downloads.csv` | One row per conda-forge package per day: cumulative downloads. |
| `pypi_daily.csv` | Downloads per day per PyPI package, excluding mirrors. Kept past pypistats' 180-day window. |
| `releases.csv` | Downloads per GitHub release for core repos, rewritten on every run. |
| `container_pulls.csv` | One row per Docker Hub or ghcr.io image per day: cumulative pulls. Docker Hub covers `quansight/qhub-*` (Nebari's pre-2022 name, no new pulls) and `artifactkeeper/*`. |
| `quay_daily.csv` | Pulls per day across quay.io/nebari, kept past quay's 90-day window. Excludes `charts/nebari-chat`, whose ~4,900 pulls a day come from an automated sync loop. |

## Setup

To track another repo, add it to `REPOS` in `scripts/snapshot.py`. Software packs come from [`tracked-packs.yaml`](https://github.com/nebari-dev/software-pack-dashboard/blob/main/tracked-packs.yaml) in software-pack-dashboard, so a new pack is tracked once it's added there.

## Run locally

```bash
GITHUB_TOKEN=$(gh auth token) python scripts/snapshot.py
```
