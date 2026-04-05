# Contributing

Thanks for helping improve this project.

## Development setup

```bash
mise install
mise run install
mise run test
```

Without `mise`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Pull request checklist

- Keep the standard-library-first approach unless a new dependency is clearly justified.
- Add or update tests for behavior changes.
- Update `README.md` and `README_EN.md` when CLI flags or outputs change.
- Update `CHANGELOG.md` for user-visible changes.
- If Apple ranges change, update both the bundled JSON and any related documentation.

## Style

- Python 3.10+ compatible.
- Prefer small, readable functions.
- Keep CLI output explicit and boring; this is infrastructure code.
