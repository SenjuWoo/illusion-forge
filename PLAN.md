# Plan

## Done in 1.0.0

- Card sniff, Koikatsu read/write through kkloader, Honey Select 2 header and lstInfo reader.
- Prompt phrase table, MCP server, CLI, write guard, bridge client.
- BepInEx maker bridge compiled for both installed games. Not installed into either game.
- Unit tests for the pieces that can run without launching the game.

## Next, only when a maker session is wanted

1. `forge build-bridge` if the DLL is stale.
2. `forge install-bridge --game kk --approve` or `--game hs2 --approve`.
3. Start the game, open the character maker, then `forge bridge ping` and `forge bridge status`.
4. `forge bridge apply` with a spec that uses only verified fields.
5. `forge bridge screenshot`, then look at the file under the game's BepInEx cache `IllusionForge` folder. The capture is end-of-frame, so read it after the frame.
6. `forge bridge dump_catalog` and keep clothing as suggestions unless the dump includes a slot and an id.

## Not in this version

Material Editor, ABMX, overlays, and any claim about the rendered face.
