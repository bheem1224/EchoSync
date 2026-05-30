#!/usr/bin/env python3
import sys
import os
import json
import ast

def error(msg):
    print(f"\033[91m[FAIL]\033[0m {msg}")

def success(msg):
    print(f"\033[92m[PASS]\033[0m {msg}")

def warn(msg):
    print(f"\033[93m[WARN]\033[0m {msg}")

class PluginASTVisitor(ast.NodeVisitor):
    def __init__(self, filepath, privileged):
        self.filepath = filepath
        self.privileged = privileged
        self.failed = False

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in ['os', 'sys', 'subprocess', 'ctypes', 'sqlite3']:
                if self.privileged:
                    warn(f"{self.filepath}:{node.lineno} - Privileged import '{alias.name}' detected.")
                else:
                    error(f"{self.filepath}:{node.lineno} - Sandbox Violation: Unauthorized import '{alias.name}'.")
                    self.failed = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            if node.module in ['os', 'sys', 'subprocess', 'ctypes', 'sqlite3']:
                if self.privileged:
                    warn(f"{self.filepath}:{node.lineno} - Privileged import '{node.module}' detected.")
                else:
                    error(f"{self.filepath}:{node.lineno} - Sandbox Violation: Unauthorized import '{node.module}'.")
                    self.failed = True
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == "threading" and node.func.attr == "Thread":
                    warn(f"{self.filepath}:{node.lineno} - Direct threading.Thread usage detected. Use native job_queue concurrency manager system.")
                elif node.func.value.id == "multiprocessing" and node.func.attr == "Process":
                    warn(f"{self.filepath}:{node.lineno} - Direct multiprocessing.Process usage detected. Use native job_queue concurrency manager system.")
                elif node.func.value.id == "asyncio" and node.func.attr in ["get_event_loop", "new_event_loop", "run"]:
                    warn(f"{self.filepath}:{node.lineno} - asyncio event loop capture detected. Use native job_queue concurrency manager system.")

            # String query mutations guard
            if node.func.attr in ["execute", "executescript", "executemany"]:
                # Check if argument is a string literal (direct un-mapped string query)
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                     warn(f"{self.filepath}:{node.lineno} - Direct string database mutation detected. Interact with tables via native platform SDK data classes (self.kvs).")

        self.generic_visit(node)

def extract_targets(obj):
    targets = []
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, str):
                targets.append(item)
            elif isinstance(item, dict):
                targets.extend(extract_targets(item))
    elif isinstance(obj, dict):
        for key, val in obj.items():
            if isinstance(val, str):
                if val.endswith('.js') or val.endswith('.css') or val.endswith('.html'):
                    targets.append(val)
            elif isinstance(val, (list, dict)):
                targets.extend(extract_targets(val))
    return targets

def validate_plugin(directory):
    print(f"\n--- Validating Plugin: {directory} ---")
    if not os.path.isdir(directory):
        error(f"Target path '{directory}' is not a directory.")
        return False

    manifest_path = os.path.join(directory, 'manifest.json')
    if not os.path.exists(manifest_path):
        error(f"Missing manifest.json in {directory}")
        return False

    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        error(f"Failed to parse manifest.json: {e}")
        return False

    plugin_id = manifest.get('id')
    author = manifest.get('author')
    name = manifest.get('name')
    privileged = manifest.get('privileged', False)

    if not plugin_id or not author or not name:
        error(f"manifest.json missing required keys (id, author, name)")
        return False

    expected_folder = plugin_id.split('.')[-1]
    actual_folder = os.path.basename(os.path.normpath(directory))

    if actual_folder != expected_folder:
        error(f"Folder name mismatch. Expected '{expected_folder}' based on manifest ID, got '{actual_folder}'.")
        return False

    # Phase 1: Dynamic Database Path & UI Asset Simulator
    simulated_stable_path = f"/data/plugins/{author}/{name}/"
    # Beta channel simulated logic would append /beta but for existence we check locally.

    ui_manifest_path = os.path.join(directory, 'ui_manifest.json')
    if os.path.exists(ui_manifest_path):
        try:
            with open(ui_manifest_path, 'r') as f:
                ui_manifest = json.load(f)
        except Exception as e:
            error(f"Failed to parse ui_manifest.json: {e}")
            return False

        assets = ui_manifest.get("assets", {})
        components = ui_manifest.get("components", {})

        all_targets = extract_targets(assets) + extract_targets(components)

        # Deduplicate and check
        for target in set(all_targets):
            parts = target.split('/')
            try:
                # find the plugin name in the URL
                idx = parts.index(expected_folder)
                relative_path = os.path.join(*parts[idx+1:])
            except ValueError:
                # If plugin name isn't directly in path, assume static/ is the root or just check relative
                if 'static' in parts:
                    idx = parts.index('static')
                    relative_path = os.path.join(*parts[idx:])
                else:
                    relative_path = target.lstrip('/')

            target_path = os.path.join(directory, relative_path)
            if not os.path.isfile(target_path):
                error(f"UI asset/component '{target}' -> physical path '{relative_path}' declared in ui_manifest.json not found at '{target_path}'.")
                return False

    # Phase 2 & 3: AST Security Sandbox Linter & Optimization Guard
    has_ast_failure = False

    # We reject any instance of an absolute import pointing back to the root `plugins.` namespace.
    # "searching for text tokens matching `from plugins.EchoSync... import ...`"
    self_import_prefix = f"plugins.{author}"

    class ScopedPluginASTVisitor(PluginASTVisitor):
        def visit_ImportFrom(self, node):
            if node.module:
                if node.module in ['os', 'sys', 'subprocess', 'ctypes', 'sqlite3']:
                    if self.privileged:
                        warn(f"{self.filepath}:{node.lineno} - Privileged import '{node.module}' detected.")
                    else:
                        error(f"{self.filepath}:{node.lineno} - Sandbox Violation: Unauthorized import '{node.module}'.")
                        self.failed = True

                # Check for absolute imports pointing to the root `plugins.` namespace.
                if node.module.startswith("plugins.") and not node.module == "plugins.plugin_system":
                    error(f"{self.filepath}:{node.lineno} - Absolute import from 'plugins.' namespace detected ('{node.module}'). Enforce intra-package relative dot-notation.")
                    self.failed = True
            self.generic_visit(node)

        def visit_Import(self, node):
            for alias in node.names:
                if alias.name in ['os', 'sys', 'subprocess', 'ctypes', 'sqlite3']:
                    if self.privileged:
                        warn(f"{self.filepath}:{node.lineno} - Privileged import '{alias.name}' detected.")
                    else:
                        error(f"{self.filepath}:{node.lineno} - Sandbox Violation: Unauthorized import '{alias.name}'.")
                        self.failed = True
                if alias.name.startswith("plugins.") and not alias.name == "plugins.plugin_system":
                    error(f"{self.filepath}:{node.lineno} - Absolute import from 'plugins.' namespace detected ('{alias.name}'). Enforce intra-package relative dot-notation.")
                    self.failed = True
            self.generic_visit(node)

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        source = f.read()
                    tree = ast.parse(source, filename=filepath)

                    visitor = ScopedPluginASTVisitor(filepath, privileged)
                    visitor.visit(tree)

                    if visitor.failed:
                        has_ast_failure = True

                except Exception as e:
                    error(f"Failed to parse Python file '{filepath}': {e}")
                    has_ast_failure = True

    if has_ast_failure:
        return False

    success(f"Plugin '{directory}' validated successfully.")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help"]:
        print("Usage: python validate_plugin.py <plugin_dir1> [plugin_dir2] ...")
        sys.exit(1 if len(sys.argv) < 2 else 0)

    all_passed = True
    for target_dir in sys.argv[1:]:
        if not validate_plugin(target_dir):
            all_passed = False

    if not all_passed:
        sys.exit(1)
