# oss-metrics

Usage numbers for OpenTeams open-source projects, shown on the [stats page](https://claude.ai/artifact/EYS6dhZKeywdY5fdMrEs87). Updated weekly by a GitHub Action.

## Where the numbers come from

| Number | Sources |
| --- | --- |
| Container pulls | Docker Hub (`quansight/qhub-*`, `artifactkeeper/*`), quay.io (`nebari`, `quansight/qhub-*`), ghcr.io (`nebari-dev`) |
| Downloads | GitHub release files, conda-forge, PyPI |
| Stars | GitHub stars on [nebari](https://github.com/nebari-dev/nebari), [nebari-infrastructure-core](https://github.com/nebari-dev/nebari-infrastructure-core), [nebi](https://github.com/nebari-dev/nebi), [artifact-keeper](https://github.com/artifact-keeper/artifact-keeper) |
| Projects | The 3 products above, plus the software packs in [tracked-packs.yaml](https://github.com/nebari-dev/software-pack-dashboard/blob/main/tracked-packs.yaml) |

## What's combined

- **Nebari = classic + NIC.** They're the old and new versions of the same product.
- **QHub counts as Nebari.** QHub is Nebari's name before 2022.

## What's left out

- **ghcr.io/artifact-keeper:** its pull rate suggests mostly CI.
- **Software pack downloads and stars:** small, and GitHub release counts miss most pack installs since packs ship as container images. Pack usage is counted in container pulls instead.
- **Stars on docs and tutorial repos:** only the products' own repos count.

## Known limits

- PyPI and quay only keep 180 and 90 days of history, so those counts start from then.
- Container pulls count every pull, including each Dask worker pod, so they're higher than the number of installs.

## Update

```bash
GITHUB_TOKEN=$(gh auth token) python scripts/snapshot.py
```
