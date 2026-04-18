with open('core/provider_base.py', 'r') as f:
    content = f.read()

orig_init = """        self.secrets = _PluginSecrets(self._name)
        self.config = _PluginConfig(self._name)
        self.core_system = _PluginCoreSystemFacade(self._name)
        self.models = _PluginModelFacade()"""

patch_init = """        self.secrets = _PluginSecrets(self._name)
        self.config = _PluginConfig(self._name)
        self.core_system = _PluginCoreSystemFacade(self._name)
        self.models = _PluginModelFacade()
        from core.tiered_logger import get_logger
        self.logger = get_logger(f"plugin.{self._name}")"""

content = content.replace(orig_init, patch_init)

with open('core/provider_base.py', 'w') as f:
    f.write(content)
