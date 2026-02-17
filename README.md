# Noctem
Self-hosted executive assistant + personal knowledge base.

## Repo layout
- `0.9.0 current version/` — **active codebase** (this is where future changes should land)
- `historical-versions/` — older snapshots and experiments (tracked in git)
- `personal-data/` — **your local runtime + private data** (ignored by git)
- `0.X.X Personal MVP/` — temporary leftover (currently locked by Windows; will be migrated into `historical-versions/` when unlocked)

## Local personal data (recommended)
All runtime state should live outside the tracked code.

1) Create your local folder (ignored by git):
- `personal-data/noctem-data/`
  - `noctem.db`, `logs/`, `sources/`, `chroma/`, `voice_journals/`, etc.

2) Point Noctem at it via environment variable:
```powershell
$env:NOCTEM_DATA_DIR = "$PWD\personal-data\noctem-data"
```
If you don’t set `NOCTEM_DATA_DIR`, Noctem defaults to `0.9.0 current version/noctem/data/`.

## Quick start (Windows / PowerShell)
```powershell
cd "0.9.0 current version"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# (recommended) keep runtime data out of git
$env:NOCTEM_DATA_DIR = "$PWD\..\personal-data\noctem-data"

python -m noctem.main init
python -m noctem.main web
```

## Obsidian
You can use Obsidian to browse the markdown docs locally.
- `.obsidian/` folders are **ignored by git** so you can keep your vault config local.

## Documentation / roadmap
- `docs/0.9.X Plan.md` — detailed roadmap for the current direction
- `docs/improvements.md` — backlog + ideas
- `docs/USER_GUIDE_v0.9.0.md` — usage guide
- `docs/Ideals_v0.9.0.md` — vision

## Notes on history cleanup
Most older folders were migrated into `historical-versions/`. Two remaining subfolders are still under `0.X.X Personal MVP/` because Windows has them locked; once unlocked (often after closing Obsidian/Explorer tabs or reboot), move them into `historical-versions/`.
