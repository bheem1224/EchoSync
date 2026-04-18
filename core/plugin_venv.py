import os
import sys
import venv
import subprocess
from pathlib import Path
from typing import List, Set
from core.tiered_logger import get_logger

logger = get_logger("plugin_venv")

def get_venv_path(plugins_dir: Path) -> Path:
    return plugins_dir / "venv"

def setup_plugin_venv(plugins_dir: Path, requirements: Set[str]):
    """
    Ensures a virtual environment exists for plugins and installs required packages.
    """
    venv_path = get_venv_path(plugins_dir)

    # 1. Create venv if it doesn't exist
    if not venv_path.exists():
        logger.info(f"Creating persistent plugin virtual environment at {venv_path}...")
        try:
            venv.create(venv_path, with_pip=True)
            logger.info("Virtual environment created successfully.")
        except Exception as e:
            logger.critical(f"Failed to create plugin virtual environment: {e}")
            raise

    # 2. Batch install requirements
    if requirements:
        logger.info(f"Installing/verifying {len(requirements)} plugin dependencies...")

        # Determine paths based on OS
        if os.name == 'nt':
            pip_executable = venv_path / "Scripts" / "pip.exe"
            site_packages = venv_path / "Lib" / "site-packages"
        else:
            pip_executable = venv_path / "bin" / "pip"
            # In Linux/macOS, site-packages path includes python version
            python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = venv_path / "lib" / python_version / "site-packages"

        if not pip_executable.exists():
            logger.critical(f"Pip executable not found in virtual environment: {pip_executable}")
            raise RuntimeError("Corrupted virtual environment")

        try:
            # Run pip install with all requirements in a single batch
            cmd = [str(pip_executable), "install", *list(requirements)]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Failed to install some plugin dependencies. Pip output:\n{result.stderr}")
            else:
                logger.debug("Plugin dependencies verified successfully.")

        except Exception as e:
            logger.error(f"Error executing pip install for plugin dependencies: {e}")

    else:
        logger.debug("No plugin dependencies to install.")

    # 3. Add venv site-packages to sys.path dynamically
    if os.name == 'nt':
         site_packages = venv_path / "Lib" / "site-packages"
    else:
         python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
         site_packages = venv_path / "lib" / python_version / "site-packages"

    site_packages_str = str(site_packages.resolve())
    if site_packages_str not in sys.path:
        # Insert at index 1 so it takes precedence over system packages but not core app files
        sys.path.insert(1, site_packages_str)
        logger.debug(f"Added plugin site-packages to sys.path: {site_packages_str}")
