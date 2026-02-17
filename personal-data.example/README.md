# personal-data (local-only)
This repo is set up so your private runtime data can live in `personal-data/` (which is ignored by git).

Recommended structure
- `personal-data/noctem-data/`
  - `noctem.db`
  - `logs/`
  - `sources/` (wiki ingestion inputs)
  - `chroma/` (vector DB)
  - `voice_journals/`
- `personal-data/sources/` (optional: other personal vaults / source dumps)
- `personal-data/research/` (optional: scratch state)

How to use
1) Copy this folder to `personal-data/`:
   - Copy `personal-data.example/` → `personal-data/`
2) Point Noctem at your runtime folder:
   - Set `NOCTEM_DATA_DIR` to `personal-data/noctem-data`

PowerShell example
$env:NOCTEM_DATA_DIR = "$PWD\personal-data\noctem-data"
