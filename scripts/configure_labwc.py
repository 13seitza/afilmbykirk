#!/usr/bin/env python3
import shutil
import sys
from pathlib import Path


KEYBIND = """    <keybind key="A-W-h">
      <action name="HideCursor" />
      <action name="WarpCursor" x="-1" y="-1" />
    </keybind>
"""


def main():
    destination = Path(sys.argv[1]).expanduser()
    source = Path("/etc/xdg/labwc/rc.xml")
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            shutil.copy2(source, destination)
        else:
            destination.write_text(
                "<?xml version=\"1.0\"?>\n"
                "<labwc_config>\n  <keyboard>\n  </keyboard>\n</labwc_config>\n"
            )

    content = destination.read_text()
    if 'key="A-W-h"' in content:
        return
    if "</keyboard>" in content:
        content = content.replace("</keyboard>", f"{KEYBIND}  </keyboard>", 1)
    else:
        closing = "</labwc_config>" if "</labwc_config>" in content else "</openbox_config>"
        content = content.replace(
            closing, f"  <keyboard>\n{KEYBIND}  </keyboard>\n{closing}", 1
        )
    destination.write_text(content)


if __name__ == "__main__":
    main()
