import re

with open('/app/core/plugin_loader.py', 'r') as f:
    content = f.read()

# Add a privileged flag to _security_scan_package
content = content.replace(
    'def _security_scan_package(self, package_dir: Path, plugin_name: str) -> bool:',
    'def _security_scan_package(self, package_dir: Path, plugin_name: str, privileged: bool = False) -> bool:'
)

content = content.replace(
    'tree = ast.parse(source, filename=str(py_file))\n\n                scanner = PluginSecurityScanner()',
    'tree = ast.parse(source, filename=str(py_file))\n\n                scanner = PluginSecurityScanner(privileged=privileged)'
)

# Update PluginSecurityScanner to accept privileged
content = content.replace(
    'def __init__(self) -> None:\n        # Each entry is (line_number, human_readable_description)\n        self.violations: list = []',
    'def __init__(self, privileged: bool = False) -> None:\n        self.privileged = privileged\n        # Each entry is (line_number, human_readable_description)\n        self.violations: list = []'
)

# Modify visit_Import and visit_ImportFrom
new_visit_import = """    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in ("os", "subprocess", "sqlite3", "sys", "importlib", "database", "inspect", "ctypes", "gc"):
                if base_module == "subprocess" and self.privileged:
                    continue
                self.violations.append((node.lineno, f"forbidden import '{alias.name}'"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in ("os", "subprocess", "sqlite3", "sys", "importlib", "database", "inspect", "ctypes", "gc"):
                if not (base_module == "subprocess" and self.privileged):
                    self.violations.append((node.lineno, f"forbidden from-import '{node.module}'"))
        self.generic_visit(node)"""

content = re.sub(
    r'    def visit_Import\(self, node: ast\.Import\) -> None:.*?def visit_Call',
    new_visit_import + '\n\n    def visit_Call',
    content,
    flags=re.DOTALL
)

# Update _scan_directory to parse privileged and pass it to _security_scan_package
# In _scan_directory:
old_manifest_logic = """                        if manifest_data.get("author") == "EchoSync" and manifest_data.get("verified_source") == "official":


                            bypass_security = True


                            logger.info(f"Bypassing security scan for official plugin: {provider_name}")"""

new_manifest_logic = """                        if manifest_data.get("author") == "EchoSync" and manifest_data.get("verified_source") == "official":
                            bypass_security = True
                            logger.info(f"Bypassing security scan for official plugin: {provider_name}")
                        privileged = manifest_data.get("privileged") is True"""

content = content.replace(old_manifest_logic, new_manifest_logic)

old_scan_call = """                if not bypass_security and not self._security_scan_package(item, provider_name):"""
new_scan_call = """                privileged = manifest_data.get("privileged") is True if 'manifest_data' in locals() else False
                if not bypass_security and not self._security_scan_package(item, provider_name, privileged=privileged):"""

content = content.replace(old_scan_call, new_scan_call)

with open('/app/core/plugin_loader.py', 'w') as f:
    f.write(content)
