# State

- Version 1.0.1.
- The package reads and writes character cards, compiles a prompt, and searches cards installed with the game.
- Game folders come from environment variables, `illusionforge.local.json`, or a Steam library.
- The maker plugin builds against the local game's BepInEx and UnityEngine assemblies. The test suite does not launch the game and does not copy the plugin into it.
- `visual_checked` stays false until a maker screenshot produced by this tool has been reviewed.
- Next, only with an explicit approve flag: install the plugin, open the character maker, then ping the bridge.
