import os

def main():
    home = "C:\\Users\\bheem"
    print(f"Scanning {home}...")
    for root, dirs, files in os.walk(home):
        # limit depth to 4
        depth = root[len(home):].count(os.sep)
        if depth > 3:
            # prune
            dirs.clear()
            continue
            
        # skip large system dirs
        if "AppData" in root and "Local" in root:
            # skip local appdata unless gemini
            if "antigravity-ide" not in root and "antigravity" not in root:
                dirs.clear()
                continue
                
        for f in files:
            if f in ("music_library.db", "working.db"):
                full_path = os.path.join(root, f)
                print(f"Found: {full_path} ({os.path.getsize(full_path)} bytes)")

if __name__ == "__main__":
    main()
