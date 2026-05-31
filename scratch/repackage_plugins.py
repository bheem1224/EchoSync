import zipfile
import os
from pathlib import Path

def zip_dir(dir_path: Path, zip_file_path: Path):
    print(f"Creating zip {zip_file_path} from {dir_path}")
    # We want to exclude ui/*, src/*, target/*, releases/*, beta.zip, and any __pycache__
    exclude_prefixes = [
        "ui/", "src/", "target/", "releases/", "beta.zip"
    ]
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(dir_path):
            # Calculate path relative to dir_path
            rel_root = Path(root).relative_to(dir_path)
            
            # Skip excluded dirs/files
            skip_dir = False
            for pfx in exclude_prefixes:
                if str(rel_root).replace('\\', '/').startswith(pfx) or "__pycache__" in str(rel_root):
                    skip_dir = True
                    break
            if skip_dir:
                continue
                
            for file in files:
                file_path = Path(root) / file
                rel_file = file_path.relative_to(dir_path)
                
                # Check file path relative
                skip_file = False
                for pfx in exclude_prefixes:
                    if str(rel_file).replace('\\', '/').startswith(pfx) or "__pycache__" in str(rel_file):
                        skip_file = True
                        break
                if skip_file:
                    continue
                
                z.write(file_path, rel_file)

plugins_dir = Path("plugins/EchoSync")
for p_dir in plugins_dir.iterdir():
    if not p_dir.is_dir():
        continue
    
    # 1. Update beta.zip
    beta_zip = p_dir / "beta.zip"
    if beta_zip.exists():
        zip_dir(p_dir, beta_zip)
        
    # 2. Update all zips in releases/
    releases_dir = p_dir / "releases"
    if releases_dir.exists():
        for zip_file in releases_dir.glob("*.zip"):
            zip_dir(p_dir, zip_file)
