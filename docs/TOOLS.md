# Tools

`doctor` reports a tool only when the executable is on disk. It looks beside each game, inside folders whose names contain "utility" or "tool", and inside the known `[UTILITY]` and `[MODDING] Tools` directories. It does not walk `abdata`.

The search recognizes KKManager, HS2CharEdit, KoikatuCharaReader, SB3Utility, ZipStudio, dnSpy, and Card Image Replacer. A missing executable is omitted. The forge does not copy these programs. Use them from the path doctor prints.

kkloader 0.1.24 is the Python reader for Koikatsu cards. It is a pip dependency of the local virtualenv, not a vendored game file.

The maker bridge is the only program this forge builds. Blender, Unity MCP, and the other tool checkouts next to this folder are not wired in. They do not read these character cards.
