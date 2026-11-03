"""Restore the seeded demo state between takes.

Deletes the SQLite database and re-runs the seed script, so logging an
outcome on camera never leaks into the next take.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.store import DB_PATH
from scripts.seed import main

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed {DB_PATH}")
    main(DB_PATH)
    print("Demo state restored. Re-run the take.")
