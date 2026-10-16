"""Start the D&D encounter manager and expose its public tools.

This module is the program's entry point.  Running ``python main.py`` calls
``main()``.  Importing ``main`` gives another Python file access to the names
listed in ``__all__`` without starting the interactive program.
"""

from character_defaults import (
    ABILITIES,
    DAMAGE_TYPES,
    PLAYER_CLASSES,
    SKILL_ABILITIES,
    WEAPONS,
    create_player_character,
    reload_character_defaults,
)
from combat import (
    ability_modifier,
    attack,
    calculate_damage,
    make_saving_throw,
    roll_dice,
    roll_expression,
)
from dm_setup import CombatSetup, setup_combat
from encounter import ENCOUNTERS_DIRECTORY, Encounter, run_encounter_console
from models import AttackResult, CharacterClassDefaults, Combatant, MonsterDefaults, Weapon
from monster_defaults import MONSTERS, create_monster, get_available_monsters, reload_monsters
from sheet_loader import (
    import_character_sheets,
    list_character_sheets,
    load_character_sheet,
    load_character_sheet_by_name,
)

__all__ = [
    "ABILITIES",
    "DAMAGE_TYPES",
    "PLAYER_CLASSES",
    "SKILL_ABILITIES",
    "WEAPONS",
    "MONSTERS",
    "AttackResult",
    "CharacterClassDefaults",
    "CombatSetup",
    "Combatant",
    "Encounter",
    "MonsterDefaults",
    "Weapon",
    "ability_modifier",
    "attack",
    "calculate_damage",
    "create_monster",
    "create_player_character",
    "get_available_monsters",
    "import_character_sheets",
    "list_character_sheets",
    "load_character_sheet",
    "load_character_sheet_by_name",
    "make_saving_throw",
    "reload_character_defaults",
    "reload_monsters",
    "roll_dice",
    "roll_expression",
    "run_encounter_console",
    "setup_combat",
]


def main() -> None:
    """Ask the DM to load an encounter or create a new one."""
    print("=== D&D Dungeon Master Assistant ===")
    saved_files = (
        list(ENCOUNTERS_DIRECTORY.glob("*.json"))
        if ENCOUNTERS_DIRECTORY.exists()
        else []
    )
    if saved_files:
        print("\nSaved encounters found:")
        for number, saved_file in enumerate(saved_files, start=1):
            print(f"  {number}. {saved_file.name}")
        choice = input(
            "Start [N]ew encounter or [L]oad saved encounter? [N/l]: "
        ).strip().lower()
        if choice == "l":
            pick = input("Enter file number or filename: ").strip()
            if pick.isdigit() and 1 <= int(pick) <= len(saved_files):
                path = saved_files[int(pick) - 1]
            else:
                target = pick if pick.endswith(".json") else f"{pick}.json"
                path = ENCOUNTERS_DIRECTORY / target
            if path.exists():
                encounter = Encounter.load(path)
                print(f"Loaded {path.name}!")
                run_encounter_console(encounter)
                return
            print("File not found; starting new encounter setup.")

    setup = setup_combat()
    encounter = Encounter(setup.combatants)
    run_encounter_console(encounter)


if __name__ == "__main__":
    main()
