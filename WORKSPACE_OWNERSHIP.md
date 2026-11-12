# Workspace ownership

- Project root: `.` (this file's directory; one owner shared by every agent).
- Active source: `.` (Illusion Forge 1.0.0, this directory). No snapshot folders.
- Versioning: semver in `VERSION` and `src/illusionforge/__init__.py`. Local only until a remote is requested.
- Repository: public GitHub remote `origin` at SenjuWoo/illusion-forge. Default branch `main`.
- Publication intent: public GitHub repository SenjuWoo/illusion-forge, MIT licence. Game installs, local indexes, and `illusionforge.local.json` stay untracked.
- Explicit GitHub publication: public and MIT for original work by default, subject to rights/platform terms; preserve existing licences. Generic publication uses the appropriate destination (Nexus for Skyrim); do not create duplicate source hosting for mods needing no compilation.
- Existing-repository maintenance: preserve its remote/visibility and follow the requested update, documentation, push and release scope.
- Read-only inputs: installed products, game Data/staging/saves and supplied references.
- Release staging: separate runtime payload from source, ownership notes, STATE/PLAN/validation, changelogs, logs and backups. Keep required licences.
- Recovery: read STATE.md and version/build/run metadata before continuing; keep the last known-good artifact.


Read the existing evidence and update the active-source/version fields before substantive edits. Do not create another owner or move files merely to match a template.
