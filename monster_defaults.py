"""Load monster presets and create NPC combatants from them.

Core monsters live together in ``data/monsters.json``.  A student can also
place one JSON file per creature in ``monsters/`` to add custom opponents.
"""

from __future__ import annotations

import json
from pathlib import Path

from character_defaults import WEAPONS
from models import DEFAULT_WEAPON, Combatant, MonsterDefaults

DATA_DIRECTORY = Path(__file__).parent / "data"
CUSTOM_MONSTERS_DIRECTORY = Path(__file__).parent / "monsters"


def _parse_monster_dict(key: str, data: dict) -> MonsterDefaults:
    """Convert one JSON monster dictionary into a typed defaults object."""
    scores = data["ability_scores"]
    scores_tuple = tuple((k.lower(), int(v)) for k, v in scores.items())
    return MonsterDefaults(
        name=data.get("name", key.capitalize()),
        armor_class=int(data["armor_class"]),
        hit_points=int(data["hit_points"]),
        ability_scores=scores_tuple,
        proficiency_bonus=int(data.get("proficiency_bonus", 2)),
        weapon=str(data["weapon"]).lower(),
        proficient_weapons=frozenset(
            weapon.lower()
            for weapon in data.get("proficient_weapons", [data["weapon"]])
        ),
        resistances=frozenset(r.lower() for r in data.get("resistances", [])),
        vulnerabilities=frozenset(v.lower() for v in data.get("vulnerabilities", [])),
        immunities=frozenset(i.lower() for i in data.get("immunities", [])),
    )


def load_monsters_from_file(
        path: Path = DATA_DIRECTORY / "monsters.json",
) -> dict[str, MonsterDefaults]:
    """Load the core monster collection from one JSON file."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as json_file:
        data = json.load(json_file)
    monsters: dict[str, MonsterDefaults] = {}
    for key, m_data in data.items():
        monsters[key.lower()] = _parse_monster_dict(key, m_data)
    return monsters


def load_custom_monster_sheets(
        directory: Path = CUSTOM_MONSTERS_DIRECTORY,
) -> dict[str, MonsterDefaults]:
    """Load every valid custom monster sheet from a directory."""
    if not directory.exists():
        return {}
    custom: dict[str, MonsterDefaults] = {}
    for path in directory.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as json_file:
                data = json.load(json_file)
            custom[path.stem.lower()] = _parse_monster_dict(path.stem, data)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            # One bad custom file should not hide the other valid monsters.
            continue
    return custom


MONSTERS: dict[str, MonsterDefaults] = load_monsters_from_file()


def reload_monsters() -> None:
    """Reload core monsters from disk without restarting Python."""
    MONSTERS.clear()
    MONSTERS.update(load_monsters_from_file())


def get_available_monsters() -> dict[str, MonsterDefaults]:
    """Get all monsters from core data and custom monsters directory."""
    all_monsters = dict(MONSTERS)
    all_monsters.update(load_custom_monster_sheets())
    return all_monsters


def create_monster(monster_type: str, *, name: str | None = None) -> Combatant:
    """Create an NPC combatant from a named monster preset."""
    monster_key = monster_type.strip().lower()
    all_monsters = get_available_monsters()
    try:
        defaults = all_monsters[monster_key]
    except KeyError as error:
        choices = ", ".join(sorted(all_monsters))
        raise ValueError(
            f"Unknown monster type {monster_type!r}. Choose from: {choices}"
        ) from error

    weapon_key = defaults.weapon.lower()
    weapon = WEAPONS.get(weapon_key, DEFAULT_WEAPON)

    return Combatant(
        name=name or defaults.name,
        armor_class=defaults.armor_class,
        hit_points=defaults.hit_points,
        max_hit_points=defaults.hit_points,
        ability_scores=dict(defaults.ability_scores),
        combatant_type="npc",
        monster_type=monster_key,
        wielded_weapon=weapon,
        proficiency_bonus=defaults.proficiency_bonus,
        proficient_weapons=set(defaults.proficient_weapons),
        resistances=set(defaults.resistances),
        vulnerabilities=set(defaults.vulnerabilities),
        immunities=set(defaults.immunities),
    )
