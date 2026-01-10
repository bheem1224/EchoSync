from pathlib import Path
import os

print(f"Path('/data').exists() = {Path('/data').exists()}")
print(f"os.path.isdir('/data') = {os.path.isdir('/data')}")
print(f"Both checks = {Path('/data').exists() and os.path.isdir('/data')}")
print(f"Path('/data') = {Path('/data')}")
