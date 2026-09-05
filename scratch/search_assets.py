from pathlib import Path

# Search C:\data\plugins
data_plugins = Path("C:/data/plugins")
print(f"Searching {data_plugins.resolve()}...")
if data_plugins.exists():
    for p in data_plugins.rglob("bundle.js"):
        print(p.resolve())
else:
    print("C:/data/plugins does not exist")

# Search project plugins folder
proj_plugins = Path("c:/Users/bheem/Nextcloud2/VS-Code-Projects/EchoSync/plugins")
print(f"Searching {proj_plugins.resolve()}...")
if proj_plugins.exists():
    for p in proj_plugins.rglob("bundle.js"):
        print(p.resolve())
