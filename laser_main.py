"""Standalone Launcher for AEPL RFID Laser Marking Utility.
Connects RFID Reader -> reads Tag ID -> updates text 't1' in EzCAD template 'test.ezd' -> marks laser.
Compatible with Windows 7 32-bit and Python 3.8 32-bit.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.laser_app import RFIDLaserApp


def main():
    app = RFIDLaserApp()
    app.run()


if __name__ == "__main__":
    main()
