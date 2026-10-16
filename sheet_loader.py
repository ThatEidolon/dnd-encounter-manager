"""Discover and import JSON character-sheet configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from character_defaults import ABILITIES, WEAPONS, create_player_character
from models import Combatant


CHARACTER_SHEETS_DIRECTORY = Path(__file__).parent / "character_sheets"

_ALLOWED_FIELDS = {
    "name", "class_type", "level", "armor_class", "hit_points", "max_hit_points", "temp_hp",
    "ability_scores", "wielded_weapon", "proficient_weapons",
    "saving_throw_proficiencies", "resistances", "vulnerabilities", "immunities",
    "conditions", "initiative",
}


def list_character_sheets(
    directory: str | Path = CHARACTER_SHEETS_DIRECTORY,
) -> list[Path]:
    """Return available JSON character sheets in stable name order."""
    sheet_directory = Path(directory)
    if not sheet_directory.exists():
        return []
    return sorted(sheet_directory.glob("*.json"), key=lambda path: path.name.lower())


def _read_sheet(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in character sheet {path.name}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"Character sheet {path.name} must contain a JSON object")

    unknown = set(data) - _ALLOWED_FIELDS
    if unknown:
        raise ValueError(
            f"Unknown fields in {path.name}: {', '.join(sorted(unknown))}"
        )
    for required in ("name", "class_type"):
        if required not in data:
            raise ValueError(f"Character sheet {path.name} is missing {required!r}")
    return data


def load_character_sheet(path: str | Path) -> Combatant:
    """Import one JSON character sheet as a Combatant."""
    sheet_path = Path(path)
    data = _read_sheet(sheet_path)

    ability_scores = data.get("ability_scores")
    if ability_scores is not None:
        if not isinstance(ability_scores, dict):
            raise ValueError("ability_scores must be a JSON object")
        missing = set(ABILITIES) - ability_scores.keys()
        if missing:
            raise ValueError(f"Missing ability scores: {', '.join(sorted(missing))}")

    weapon_name = data.get("wielded_weapon")
    weapon = None
    if weapon_name is not None:
        try:
            weapon = WEAPONS[str(weapon_name).lower()]
        except KeyError as error:
            raise ValueError(f"Unknown weapon {weapon_name!r} in {sheet_path.name}") from error

    character = create_player_character(
        str(data["name"]),
        str(data["class_type"]),
        ability_scores=ability_scores,
        armor_class=data.get("armor_class"),
        hit_points=data.get("hit_points"),
        level=int(data.get("level", 1)),
        wielded_weapon=weapon,
    )

    if "max_hit_points" in data:
        character.max_hit_points = int(data["max_hit_points"])
    if "temp_hp" in data:
        character.temp_hp = int(data["temp_hp"])
    if "conditions" in data and isinstance(data["conditions"], list):
        character.conditions = {c.lower() for c in data["conditions"]}

    for field_name in (
        "proficient_weapons", "saving_throw_proficiencies", "resistances",
        "vulnerabilities", "immunities",
    ):
        if field_name in data:
            values = data[field_name]
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise ValueError(f"{field_name} must be a JSON list of strings")
            setattr(character, field_name, {item.lower() for item in values})

    return character


def load_character_sheet_by_name(
    sheet_name: str,
    directory: str | Path = CHARACTER_SHEETS_DIRECTORY,
) -> Combatant:
    """Load a sheet by filename or stem without allowing path traversal."""
    requested = sheet_name.strip().lower()
    if requested.endswith(".json"):
        requested = requested[:-5]
    available = {path.stem.lower(): path for path in list_character_sheets(directory)}
    try:
        path = available[requested]
    except KeyError as error:
        choices = ", ".join(sorted(available)) or "none"
        raise ValueError(
            f"Unknown character sheet {sheet_name!r}. Available sheets: {choices}"
        ) from error
    return load_character_sheet(path)


def import_character_sheets(
    directory: str | Path = CHARACTER_SHEETS_DIRECTORY,
) -> list[Combatant]:
    """Import every character sheet from a directory."""
    return [load_character_sheet(path) for path in list_character_sheets(directory)]
