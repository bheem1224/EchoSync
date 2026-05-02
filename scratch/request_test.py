import ast
from core.plugin_loader import PluginSecurityScanner

source = """
import requests
requests.get("http://evil.com")
"""

tree = ast.parse(source)
s = PluginSecurityScanner()
s.visit(tree)
print(s.violations)
