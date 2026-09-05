import zipfile
from pathlib import Path

plugins_dir = Path("plugins/EchoSync")
for p_dir in plugins_dir.iterdir():
    if not p_dir.is_dir():
        continue
    beta_zip = p_dir / "beta.zip"
    if beta_zip.exists():
        try:
            with zipfile.ZipFile(beta_zip, "r") as z:
                # read __init__.py
                init_content = z.read("__init__.py").decode("utf-8", errors="ignore")
                print(f"--- {p_dir.name} beta.zip __init__.py ---")
                print(init_content.strip())
        except Exception as e:
            print(f"Error reading {beta_zip}: {e}")

    # Check release zips in releases/
    releases_dir = p_dir / "releases"
    if releases_dir.exists():
        for zip_file in releases_dir.glob("*.zip"):
            try:
                with zipfile.ZipFile(zip_file, "r") as z:
                    init_content = z.read("__init__.py").decode(
                        "utf-8", errors="ignore"
                    )
                    print(f"--- {p_dir.name} {zip_file.name} __init__.py ---")
                    print(init_content.strip())
            except Exception as e:
                print(f"Error reading {zip_file}: {e}")
