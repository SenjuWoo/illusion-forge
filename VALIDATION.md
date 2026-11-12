# Validation

## Automated

- `python -m unittest discover -s tests -q` with `PYTHONPATH=src` covers card sniffing, the phrase table, temporary card edits, the game-folder write guard, the bridge client, MCP framing, and library ranking.
- Tests that open a real card run only when that card is installed. A checkout with no game configured skips them.
- `dotnet run --project plugins/JsonMini.Tests -c Release` checks the JSON reader compiled into the plugin. Exit 0 prints `jsonmini ok`.
- Continuous integration runs the Python suite on Ubuntu and Windows, and the JSON self-test on Ubuntu. It does not build the BepInEx plugin, because that build references the game's own assemblies.

## Checked by hand against installed cards

- An unmodified save returns the original bytes.
- A Honey Select 2 face phrase is applied as a delta on the chosen card's current slider.
- Koikatsu height is body index 0. An out-of-range index does not mark the card dirty.
- Honey Select 2 coordinate bytes are not parsed as a Koikatsu outfit. Those bytes stay unchanged across a face edit.
- `make` copies a library card outside the game and leaves the source file's hash unchanged.

## Not covered

- The game is not launched.
- The plugin is not installed by the test suite.
- No maker screenshot has been reviewed. `visual_checked` is false.
- Clothing words are not item ids.
- `dump_catalog` and `screenshot` have not been run against a live process.
