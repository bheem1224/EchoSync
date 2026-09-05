import os


def main():
    root_path = "C:\\Users\\bheem\\Nextcloud2"
    print(f"Scanning {root_path}...")
    for root, dirs, files in os.walk(root_path):
        depth = root[len(root_path) :].count(os.sep)
        if depth > 4:
            dirs.clear()
            continue
        for f in files:
            if f.endswith(".db") and not ".git" in root and not ".venv" in root:
                full_path = os.path.join(root, f)
                print(f"Found: {full_path} ({os.path.getsize(full_path)} bytes)")


if __name__ == "__main__":
    main()
