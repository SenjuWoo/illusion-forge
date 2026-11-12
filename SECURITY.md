# Security

Report a vulnerability through private vulnerability reporting on this repository. Do not open a public issue for an unfixed security bug.

The supported line is the current release.

The maker plugin listens on 127.0.0.1 only. Do not publish that port. The plugin does not accept a destination inside a game folder. The command-line tool refuses those writes unless `--approve-gamedir` is passed on purpose.
