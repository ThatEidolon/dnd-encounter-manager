"""Interactive Dungeon Master combat setup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from character_defaults import PLAYER_CLASSES
from models import Combatant
from monster_defaults import MONSTERS, create_monster, get_available_monsters
from sheet_loader import list_character_sheets, load_character_sheet_by_name


@dataclass
class CombatSetup:
    players: list[Combatant]
    npcs: list[Combatant]

    @property
    def combatants(self) -> list[Combatant]:
        return [*self.players, *self.npcs]


def _prompt_count(
    prompt: str,
    input_func: Callable[[str], str],
    output_func: Callable[[str], None],
) -> int:
    while True:
        try:
            value = int(input_func(prompt))
            if value < 0:
                raise ValueError
            return value
        except ValueError:
            output_func("Please enter a whole number of 0 or greater.")


def setup_combat(
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> CombatSetup:
    """Prompt the DM for player sheets/classes and typed NPC opponents."""
    output_func("\n=== D&D Combat Setup ===")
    sheet_names = [path.stem for path in list_character_sheets()]
    output_func(f"Character sheets: {', '.join(sheet_names) or 'none'}")
    output_func(f"Player classes: {', '.join(sorted(PLAYER_CLASSES))}")

    players: list[Combatant] = []
    player_count = _prompt_count("How many player characters? ", input_func, output_func)
    for index in range(player_count):
        while True:
            selection = input_func(
                f"Player {index + 1} sheet name or class type: "
            ).strip().lower()
            if selection in {name.lower() for name in sheet_names}:
                players.append(load_character_sheet_by_name(selection))
                break
            if selection in PLAYER_CLASSES:
                name = input_func(f"Name for the {selection}: ").strip()
                players.append(Combatant.from_player_class(name, selection))
                break
            output_func("Choose one of the listed character sheets or player classes.")

    available_monsters = get_available_monsters()
    output_func(f"Monster types: {', '.join(sorted(available_monsters))}")
    npcs: list[Combatant] = []
    npc_count = _prompt_count("How many NPCs or monsters? ", input_func, output_func)
    for index in range(npc_count):
        while True:
            monster_type = input_func(f"NPC {index + 1} type: ").strip().lower()
            if monster_type in available_monsters:
                same_type_count = sum(npc.monster_type == monster_type for npc in npcs)
                display_name = f"{available_monsters[monster_type].name} {same_type_count + 1}"
                npcs.append(create_monster(monster_type, name=display_name))
                break
            output_func("Choose one of the listed monster types.")

    setup = CombatSetup(players=players, npcs=npcs)
    output_func("\nCombatants:")
    for combatant in setup.combatants:
        kind = combatant.character_class or combatant.monster_type or combatant.combatant_type
        weapon = combatant.wielded_weapon.name if combatant.wielded_weapon else "unarmed"
        output_func(
            f"- {combatant.name}: {kind}, AC {combatant.armor_class}, "
            f"HP {combatant.hit_points}/{combatant.max_hit_points}, weapon {weapon}"
        )
    return setup
