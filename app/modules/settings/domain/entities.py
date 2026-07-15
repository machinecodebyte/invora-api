from dataclasses import dataclass

from app.modules.settings.domain.enums import SettingsCategory


@dataclass(frozen=True)
class SettingsCategoryDefinition:
    category: SettingsCategory
    fields: tuple[str, ...]
