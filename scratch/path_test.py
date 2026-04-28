from pathlib import Path
import os

p = Path(__file__).resolve()
print(f"File: {p}")
print(f"Parent: {p.parent}")
print(f"Parent Parent: {p.parent.parent}")
print(f"Plugins dir: {p.parent.parent / 'plugins'}")
print(f"Plugins dir exists: {(p.parent.parent / 'plugins').exists()}")
