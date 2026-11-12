# Architecture

```text
prompt or spec JSON
        |
        v
compile_prompt          # phrase table, no model
        |
        v
apply_spec              # only fields present on that card
        |
        +--> card file outside the game
        |
        +--> maker bridge on 127.0.0.1:47331
                 |
                 v
             main-thread reflection on the maker preview
```

Koikatsu cards go through kkloader. Honey Select 2 cards use the same lstInfo block table after a longer header: language, user id, data id. Custom and Parameter are parsed when they are read or edited. Every other block, including Coordinate, is kept as the original bytes.

The plugin does not reference Assembly-CSharp. It finds `KKAPI.Maker.MakerAPI` in the loaded assemblies, asks for the character control, and sets fields by name. Unity work runs on the main thread because `Update` drains a queue. The accept thread only reads and writes sockets.

A missing maker, a missing field, or a method that is not zero-arg comes back as JSON. The command does not pretend the change was drawn.
