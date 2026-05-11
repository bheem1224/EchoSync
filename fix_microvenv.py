import re

with open("core/plugin_store.py", "r") as f:
    content = f.read()

# Target injection point: right after atomic swap or right after state synchronization
# We will do it after atomic swap (around line 529-530)
target_str = """                os.rename(str(tmp_dir), str(target_dir))
                logger.info(f"Successfully installed {plugin_id} artifact via atomic swap")"""

injection = """                os.rename(str(tmp_dir), str(target_dir))
                logger.info(f"Successfully installed {plugin_id} artifact via atomic swap")

                # Task 1: Localized Dependency Installation (Micro-Venv)
                requirements_file = target_dir / "requirements.txt"
                if requirements_file.exists():
                    logger.info(f"Found requirements.txt for {plugin_id}, installing into micro-venv")
                    micro_venv_dir = target_dir / "micro-venv"
                    import subprocess
                    try:
                        # Use uv pip install --target to isolate dependencies
                        subprocess.run(
                            ["uv", "pip", "install", "--target", str(micro_venv_dir), "-r", str(requirements_file)],
                            check=True,
                            capture_output=True,
                            text=True
                        )
                        logger.info(f"Successfully installed micro-venv dependencies for {plugin_id}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to install micro-venv dependencies for {plugin_id}: {e.stderr}")
                        # Depending on strictness, we could return False here, but we will let it continue
                        # and log the error. Usually a broken requirements.txt means the plugin might fail to load.
"""

content = content.replace(target_str, injection)

with open("core/plugin_store.py", "w") as f:
    f.write(content)
