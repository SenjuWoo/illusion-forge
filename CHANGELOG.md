# Changelog

## Unreleased

- README: `make` has no `--approve-gamedir` flag and always refuses a destination inside a game install; only `apply` takes the override.

## 1.0.2

- Honey Select 2 eye color now applies. These cards keep the iris color in `pupil[].pupilColor`, not `baseColor`, so `make`, `apply` and the maker plugin used to skip every Honey Select 2 eye color with "pupil baseColor was not on this card". The index and `inspect` now read the same key, and the index format moved to version 2, so run `illusionforge index` once to refresh the cache.
- A color word is no longer a character name. "blue eyes" used to pick a card named "Blue" as a confident name hit; feature pairs such as "blue eyes" and "big nose" are now left out of the whole-name match. `named "Blue"` still finds that card.
- README rebuilt with real-run terminal shots and the repository mark (`docs/icon.svg`).
- The maker plugin changed (eye color fallback), so this release ships `IllusionForge-1.0.2-maker-bridge.zip`. It was compiled for both games and not loaded in a running maker.

## 1.0.1

- `forge.py` started with an interpreter that lacks the card libraries now prints one JSON error naming the missing module and the two ways to fix it, and exits 4. Before, it ended in an import traceback.
- `forge.cmd`, `START-HERE.bat` and `Run-Tests.bat` pin delayed expansion off, so a folder whose name contains `!` is passed through intact.

## 1.0.0

- Local CLI and stdio MCP for Koikatsu and Honey Select 2 character cards.
- Offline prompt compiler for a fixed set of face phrases, colors, height, name, and sex.
- Honey Select 2 face slider names in a data file with a cited source. Koikatsu uses numeric face indexes.
- Maker bridge plugin that listens on loopback and applies fields by reflection while the maker is open.
- Tests cover sniffing, compilation, temporary card round-trips, the game-folder write guard, the bridge client, and MCP.
- The plugin is compiled for both games. It is not installed, and the maker was not launched.
- "short hair" is not a height. A later real height in the same sentence still is. "school uniform" does not also emit "uniform".
- An out-of-range slider does not mark the card dirty. Bridge face names are translated to indexes in the Python client. A timed-out command is dropped if the game has not started it, and refresh runs only for fields that were applied.
- `index`, `match`, and `make` search the character cards already installed with the games. `make` copies the closest card and applies the prompt on top of it. The card's outfit is kept. Face phrases are deltas from that card.
- Game installs are read from `ILLUSION_KK_ROOT`, `ILLUSION_HS2_ROOT`, `illusionforge.local.json`, or a Steam library. No install path is built into the package.
- Match prefers the stock `female` or `male` card when the prompt names nobody, ranks a folder named `Old` below the current copy, and breaks equal names toward the newer file. A name that is not installed returns no card. The index is parsed once per process, and `make` does not parse the chosen card twice.
