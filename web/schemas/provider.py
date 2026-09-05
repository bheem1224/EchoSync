from dataclasses import dataclass, field


@dataclass
class ProviderSchema:
    name: str
    capabilities: list[str] = field(default_factory=list)
    scopes: list[str] = field(
        default_factory=list
    )  # library, sync, search, download, utility
    priority: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "capabilities": self.capabilities,
            "scopes": self.scopes,
            "priority": self.priority,
        }
