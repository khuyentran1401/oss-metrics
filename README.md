# oss-metrics

Daily snapshots of public GitHub stats for OpenTeams open-source repos.

## Why

GitHub only reports the current release download total, with no record of when downloads happened. Snapshotting it regularly is the only way to show download growth over time, which says more to investors than a single total.

Stars and forks don't need this, since GitHub records when each star and fork happened. They're included because they come with the same API call.

## Data

`data/repo_stats.csv` has one row per repo per day: group (`core` or `software-pack`), stars, forks, and release_downloads (cumulative). Sum the `software-pack` rows to report packs as one line.

## Setup

To track another repo, add it to `REPOS` in `scripts/snapshot.py`. Software packs come from [`tracked-packs.yaml`](https://github.com/nebari-dev/software-pack-dashboard/blob/main/tracked-packs.yaml) in software-pack-dashboard, so a new pack is tracked once it's added there.

## Run locally

```bash
GITHUB_TOKEN=$(gh auth token) python scripts/snapshot.py
```
