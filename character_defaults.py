"""Shared 5e character data and level-one player-class presets loaded from text/JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from models import CharacterClassDefaults, Combatant, DEFAULT_WEAPON, Weapon


ABILITIES = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)

DAMAGE_TYPES = (
    "acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic",
    "piercing", "poison", "psychic", "radiant", "slashing", "thunder",
)

SKILL_ABILITIES = {
    "acrobatics": "dexterity",
    "animal handling": "wisdom",
    "arcana": "intelligence",
    "athletics": "strength",
    "deception": "charisma",
    "history": "intelligence",
    "insight": "wisdom",
    "intimidation": "charisma",
    "investigation": "intelligence",
    "medicine": "wisdom",
    "nature": "intelligence",
    "perception": "wisdom",
    "performance": "charisma",
    "persuasion": "charisma",
    "religion": "intelligence",
    "sleight of hand": "dexterity",
    "stealth": "dexterity",
    "survival": "wisdom",
}

DATA_DIRECTORY = Path(__file__).parent / "data"


def _scores(**scores: int) -> tuple[tuple[str, int], ...]:
    return tuple(scores.items())


def load_weapons_from_file(path: Path = DATA_DIRECTORY / "weapons.json") -> dict[str, Weapon]:
    if not path.exists():
        return {
            "shortsword": DEFAULT_WEAPON,
            "sword": Weapon("sword", "1d8", "slashing"),
            "longsword": Weapon("longsword", "1d8", "slashing"),
        }
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    weapons: dict[str, Weapon] = {}
    for name, w_data in data.items():
        key = name.lower()
        if (
            key == "shortsword"
            and w_data.get("damage_dice") == DEFAULT_WEAPON.damage_dice
            and w_data.get("damage_type") == DEFAULT_WEAPON.damage_type
            and w_data.get("ability", "dexterity") == DEFAULT_WEAPON.ability
        ):
            weapons[key] = DEFAULT_WEAPON
        else:
            weapons[key] = Weapon(
                name=name,
                damage_dice=w_data["damage_dice"],
                damage_type=w_data["damage_type"],
                ability=w_data.get("ability", "strength"),
                is_ranged=w_data.get("is_ranged", False),
            )
    return weapons


def load_classes_from_file(
    path: Path = DATA_DIRECTORY / "classes.json",
) -> dict[str, CharacterClassDefaults]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    classes: dict[str, CharacterClassDefaults] = {}
    for name, c_data in data.items():
        scores_tuple = tuple((k.lower(), int(v)) for k, v in c_data["ability_scores"].items())
        classes[name.lower()] = CharacterClassDefaults(
            name=name.lower(),
            hit_die=int(c_data["hit_die"]),
            armor_class=int(c_data["armor_class"]),
            ability_scores=scores_tuple,
            saving_throws=frozenset(s.lower() for s in c_data["saving_throws"]),
            starter_weapon=str(c_data["starter_weapon"]).lower(),
        )
    return classes


WEAPONS: dict[str, Weapon] = load_weapons_from_file()
PLAYER_CLASSES: dict[str, CharacterClassDefaults] = load_classes_from_file()


def reload_character_defaults() -> None:
    """Reload weapons and player classes from disk without restarting Python."""
    global WEAPONS, PLAYER_CLASSES
    WEAPONS.clear()
    WEAPONS.update(load_weapons_from_file())
    PLAYER_CLASSES.clear()
    PLAYER_CLASSES.update(load_classes_from_file())


def create_player_character(
    name: str,
    class_type: str,
    *,
    ability_scores: dict[str, int] | None = None,
    armor_class: int | None = None,
    hit_points: int | None = None,
    level: int = 1,
    wielded_weapon: Weapon | None = None,
) -> Combatant:
    """Build a player from a class preset, with optional sheet overrides."""
    class_key = class_type.strip().lower()
    try:
        defaults = PLAYER_CLASSES[class_key]
    except KeyError as error:
        choices = ", ".join(sorted(PLAYER_CLASSES))
        raise ValueError(
            f"Unknown player class {class_type!r}. Choose from: {choices}"
        ) from error

    scores = dict(defaults.ability_scores) if ability_scores is None else ability_scores.copy()
    missing = set(ABILITIES) - scores.keys()
    if missing:
        raise ValueError(f"Missing ability scores: {', '.join(sorted(missing))}")

    weapon = wielded_weapon or WEAPONS.get(defaults.starter_weapon, DEFAULT_WEAPON)
    con_mod = (scores["constitution"] - 10) // 2
    starting_hp = defaults.hit_die + con_mod
    actual_hp = starting_hp if hit_points is None else hit_points
    return Combatant(
        name=name,
        armor_class=defaults.armor_class if armor_class is None else armor_class,
        hit_points=actual_hp,
        max_hit_points=actual_hp,
        ability_scores=scores,
        combatant_type="player",
        character_class=defaults.name,
        level=level,
        hit_die=defaults.hit_die,
        wielded_weapon=weapon,
        proficiency_bonus=2 + max(0, level - 1) // 4,
        proficient_weapons={weapon.name},
        saving_throw_proficiencies=set(defaults.saving_throws),
    )
