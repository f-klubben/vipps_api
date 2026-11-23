# Releasing

Versions reach PyPI through `.github/workflows/publish.yml`, which runs on every push to the `release` branch.

## One-time setup

The PyPI project trusts this repository, so no token is stored anywhere: owner `f-klubben`, repository `vipps_api`, workflow `publish.yml`, environment `pypi`. Those four values must match the publisher registered on PyPI, otherwise the upload fails at the OIDC exchange.

## Publishing a version

    git switch release
    git merge main                      # bring in the code being released
    # bump __version__ in src/vipps_api/__init__.py, then
    git commit -am "Bump version to 0.1.1"
    git push

The workflow reads `__version__`, checks PyPI for that exact version, and only then runs the tests, builds and uploads. A version PyPI already has is skipped, so re-pushing or re-running the job is harmless and never overwrites.

Watch it with `gh run list --workflow=publish.yml --limit=1`, and confirm the result at https://pypi.org/project/vipps-api/.

## If a release is broken

Uploads cannot be replaced. Fix the code, bump the version higher, and push again. To stop `pip install` from picking the broken version, yank it on PyPI (Manage → Releases → Yank) — yanking hides it from resolvers without deleting it.

## Branch model

`main` is development. `release` carries the version being shipped and is bumped only for releases, so it is normally ahead of `main` by version-bump commits alone; merging `main` in before a bump keeps them together.
