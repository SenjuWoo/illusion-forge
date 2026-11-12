# Maker bridge

The plugin id is `local.illusionforge.makerbridge`. Default port is 47331 on 127.0.0.1. The port is a BepInEx config entry named `Network` / `Port`. No other interface is opened.

One JSON object per line, request and response. Lines over 1MB are rejected. A client that throws does not stop the listener.

## Operations

- `ping` returns the process name and `kk` or `hs2` when the process name starts with `Koikatu` or `HoneySelect2`.
- `status` reports whether `KKAPI.Maker.MakerAPI` is loaded, `InsideMaker` when that member exists, and whether `GetCharacterControl` returned an object.
- `apply` sets numeric face and body indexes, `height` on Koikatsu only, hair and eye and eyebrow and skin colors, name fields that exist, and `sex` when the field exists. The Python client rewrites Honey Select 2 face names to those indexes before the send. The plugin still accepts only numeric keys and Koikatsu `height`. Refresh runs only for a field that was actually applied: face shape, eye or eyebrow color, body shape, skin color, or hair color. A client that times out marks the job dropped when the main thread has not started it, so that command is not applied afterwards. If the main thread has already started, the client waits once more and can still report a timeout after the apply finishes.
- `dump_catalog` looks for `ChaListControl` and a one-argument `GetCategoryInfo` whose argument is an enum. It returns at most 24 categories and 60 items each. If that shape is not there, the response says so.
- `screenshot` calls `ScreenCapture.CaptureScreenshot(string)` when that exact method exists. The file is under BepInEx cache `IllusionForge`. The write happens at the end of the frame.

`visual_checked` is false on every response. The bridge does not save the card. Save in the maker, or write a card with the Python tool to a path outside the game.

## Build

`forge build-bridge` compiles `plugins/MakerBridge` against each installed game and runs the JSON self-test. Output:

- `build/bridge/kk/IllusionForge.MakerBridge.dll`
- `build/bridge/hs2/IllusionForge.MakerBridge.dll`

`forge install-bridge --game kk --approve` copies that DLL to `BepInEx\plugins\IllusionForge`. Without `--approve` it refuses.

## What is not called

`ChangeClothes`, `Reload`, and any `ChangeSettingHair` overload that takes parameters. Those names were seen as strings in `Assembly-CSharp` and their signatures were not decompiled, so the plugin does not guess arguments.
