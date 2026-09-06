"""Pydantic schemas for system settings requests and responses."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class LibraryImportSettings(BaseModel):
    group_singles: bool | None = Field(
        default=True,
        description="Consolidate non-album tracks into an artist 'Singles' directory",
    )
    singles_pattern: str | None = Field(
        default="{Artist}/Singles/{Track} - {Title}.{ext}",
        description="Renaming pattern for standalone singles/recordings",
    )
    renaming_pattern: str | None = Field(
        default=None,
        description="Renaming pattern for albums",
    )
    auto_import_enabled: bool | None = Field(
        default=False,
        description="Whether auto-import is enabled",
    )

    model_config = ConfigDict(extra="allow")


class MetadataEnhancementSettings(BaseModel):
    auto_import: bool | None = Field(
        default=False,
        description="Whether auto-import is enabled",
    )
    conflict_resolution: str | None = Field(
        default="keep_both",
        description="Conflict resolution strategy",
    )
    naming_template: str | None = Field(
        default="{Artist}/{Album}/{Track} - {Title}.{ext}",
        description="Naming template for album tracks",
    )
    prefer_canonical_studio_album: bool | None = Field(
        default=True,
        description="Whether to prefer canonical studio albums over compilations and repacks",
    )

    model_config = ConfigDict(extra="allow")


class SystemSettingsPatchRequest(BaseModel):
    log_level: str | None = None
    active_media_server: str | None = None
    active_download_client: str | None = None
    metadata_enhancement: MetadataEnhancementSettings | dict[str, Any] | None = None
    library_import: LibraryImportSettings | dict[str, Any] | None = None
    quality_profiles: list[Any] | None = None
    scan_interval: int | None = None
    file_rename_template: str | None = None
    match_threshold: float | int | None = None
    storage: dict[str, Any] | None = None
    theme: str | None = None
    active_matching_engine: str | None = None
    account_mapping: dict[str, Any] | None = None
    custom_ui_path: str | None = None

    model_config = ConfigDict(extra="allow")
