"""Allow `python -m illusionforge`.

Needs the src directory on PYTHONPATH, or an editable install.
"""

from illusionforge.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
