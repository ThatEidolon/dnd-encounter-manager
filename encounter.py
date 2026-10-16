"""Manage initiative, turns, saved encounters, and the live DM console.

``Encounter`` contains the state and small operations for a battle.  The
``run_encounter_console`` function is the user interface that translates text
commands into those operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from combat import (
    DEFAULT_ROLLER,
    Roller,
    attack,
    make_saving_throw,
    roll_expression,
)
from models import Combatant
from monster_defaults import create_monster, get_available_monsters

ENCOUNTERS_DIRECTORY = Path(__file__).parent / "encounters"


def _find_target(
        encounter: Encounter,
        target_name: str,
        output_func: Callable[[str], None],
) -> Combatant | None:
    """Find a target and display a consistent message when it is missing."""
    target = encounter.find_combatant(target_name)
    if target is None:
        output_func(f"Combatant {target_name!r} not found.")
    return target


def _read_manual_d20(
        encounter: Encounter,
        combatant: Combatant,
        input_func: Callable[[str], str],
) -> int | None:
    """Read a physical d20 result when the encounter uses manual mode."""
    if encounter.roll_mode != "manual":
        return None
    value = input_func(
        f"Enter physical d20 roll for {combatant.name}: "
    ).strip()
    return int(value) if value.isdigit() else None


def _read_target_and_amount(
        encounter: Encounter,
        arguments: list[str],
        usage: str,
        output_func: Callable[[str], None],
) -> tuple[Combatant, int] | None:
    """Parse a target name and whole-number amount from command arguments."""
    if len(arguments) < 2:
        output_func(usage)
        return None

    amount_text = arguments[-1]
    target_name = " ".join(arguments[:-1])
    target = _find_target(encounter, target_name, output_func)
    if target is None:
        return None
    try:
        amount = int(amount_text)
    except ValueError:
        output_func("Amount must be a whole number.")
        return None
    return target, amount


class Encounter:
    """Track round number, turn order, and every combatant in one battle."""

    def __init__(
            self,
            combatants: list[Combatant] | None = None,
            *,
            round_number: int = 1,
            turn_index: int = 0,
            roll_mode: str = "auto",
    ) -> None:
        self.combatants: list[Combatant] = combatants or []
        self.round_number: int = round_number
        self.turn_index: int = turn_index
        self.roll_mode: str = roll_mode
        self.initiative_rolled: bool = any(
            combatant.initiative > 0 for combatant in self.combatants
        )

    @property
    def active_combatant(self) -> Combatant | None:
        """Return the combatant whose turn it is, or ``None`` if empty."""
        if not self.combatants:
            return None
        self.turn_index = max(0, min(self.turn_index, len(self.combatants) - 1))
        return self.combatants[self.turn_index]

    def roll_initiative(
            self,
            roller: Roller = DEFAULT_ROLLER,
            manual_rolls: dict[str, int] | None = None,
    ) -> None:
        """Roll initiative and sort combatants into their turn order."""
        manual_rolls = manual_rolls or {}
        for combatant in self.combatants:
            if combatant.name in manual_rolls:
                combatant.initiative = manual_rolls[combatant.name]
            else:
                dex_mod = combatant.modifier("dexterity")
                combatant.initiative = roller.randint(1, 20) + dex_mod
        self.sort_by_initiative()
        self.initiative_rolled = True
        self.turn_index = 0

    def sort_by_initiative(self) -> None:
        """Sort highest initiative first, using Dexterity and name as ties."""
        self.combatants.sort(
            key=lambda c: (
                c.initiative,
                c.ability_scores.get("dexterity", 10),
                c.name,
            ),
            reverse=True,
        )

    def next_turn(self) -> tuple[Combatant | None, bool]:
        """Advance a turn and report whether a new round started."""
        if not self.combatants:
            return None, False

        round_advanced = False
        attempts = 0

        while attempts < len(self.combatants):
            self.turn_index += 1
            if self.turn_index >= len(self.combatants):
                self.turn_index = 0
                self.round_number += 1
                round_advanced = True

            active = self.active_combatant
            # Dead NPCs stay in the table but do not receive another turn.
            if active and active.combatant_type == "npc" and not active.is_alive:
                attempts += 1
                continue
            return active, round_advanced

        return self.active_combatant, round_advanced

    def prev_turn(self) -> Combatant | None:
        """Move backward one turn and return the newly active combatant."""
        if not self.combatants:
            return None
        self.turn_index -= 1
        if self.turn_index < 0:
            if self.round_number > 1:
                self.round_number -= 1
            self.turn_index = len(self.combatants) - 1
        return self.active_combatant

    def find_combatant(self, query: str) -> Combatant | None:
        """Find a combatant by list number or a case-insensitive name."""
        cleaned_query = query.strip().lower()
        if not cleaned_query:
            return None

        # People count from 1, but Python list indexes begin at 0.
        if cleaned_query.isdigit():
            index = int(cleaned_query) - 1
            if 0 <= index < len(self.combatants):
                return self.combatants[index]

        for combatant in self.combatants:
            if combatant.name.lower() == cleaned_query:
                return combatant

        for combatant in self.combatants:
            if combatant.name.lower().startswith(cleaned_query):
                return combatant

        for combatant in self.combatants:
            if cleaned_query in combatant.name.lower():
                return combatant
        return None

    def add_combatant(self, combatant: Combatant) -> None:
        """Add a combatant and restore initiative order when necessary."""
        self.combatants.append(combatant)
        if self.initiative_rolled:
            self.sort_by_initiative()

    def remove_combatant(self, query: str) -> Combatant | None:
        """Remove and return a matching combatant, if one exists."""
        target = self.find_combatant(query)
        if target:
            idx = self.combatants.index(target)
            self.combatants.remove(target)
            if self.turn_index >= len(self.combatants):
                self.turn_index = max(0, len(self.combatants) - 1)
            elif idx < self.turn_index:
                self.turn_index = max(0, self.turn_index - 1)
        return target

    def check_battle_status(self) -> str | None:
        """Return a victory, defeat, or warning message when appropriate."""
        players = [
            combatant
            for combatant in self.combatants
            if combatant.combatant_type == "player"
        ]
        npcs = [
            combatant
            for combatant in self.combatants
            if combatant.combatant_type == "npc"
        ]

        players_conscious = [c for c in players if c.is_conscious]
        players_alive = [c for c in players if c.is_alive]
        npcs_alive = [c for c in npcs if c.is_alive]

        if npcs and not npcs_alive:
            return "VICTORY: All enemy NPCs have been defeated!"
        if players and not players_alive:
            return "DEFEAT: All player characters have fallen!"
        if players and not players_conscious:
            return "WARNING: All player characters are down or unconscious!"
        return None

    def status_table(self) -> str:
        """Build a multi-line table showing initiative and current health."""
        if not self.combatants:
            return "No combatants in encounter."

        lines = [
            f"=== Round {self.round_number} ===",
            (
                f"{'':3} {'#':<2} {'Init':<5} {'Name':<16} "
                f"{'Type':<7} {'AC':<4} {'HP':<14} {'Status'}"
            ),
            "-" * 68,
        ]

        for number, combatant in enumerate(self.combatants, start=1):
            is_active = (
                    self.turn_index == number - 1 and self.initiative_rolled
            )
            marker = ">>>" if is_active else "   "
            hp_text = f"{combatant.hit_points}/{combatant.max_hit_points}"
            if combatant.temp_hp > 0:
                hp_text += f" (+{combatant.temp_hp})"

            status_tags = []
            if not combatant.is_alive:
                status_tags.append("[DEAD]")
            elif not combatant.is_conscious:
                if combatant.combatant_type == "player":
                    if combatant.stable:
                        status_tags.append("[STABLE]")
                    else:
                        status_tags.append(
                            "[DOWN DS:"
                            f"{combatant.death_saves_success}S/"
                            f"{combatant.death_saves_failure}F]"
                        )
                else:
                    status_tags.append("[UNCONSCIOUS]")
            for condition in sorted(combatant.conditions):
                if condition not in {"dead", "unconscious"}:
                    status_tags.append(f"[{condition.upper()}]")

            status_str = " ".join(status_tags) if status_tags else "Normal"
            lines.append(
                f"{marker} {number:<2} {combatant.initiative:<5} "
                f"{combatant.name:<16} {combatant.combatant_type:<7} "
                f"{combatant.armor_class:<4} {hp_text:<14} {status_str}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Return the encounter state in a JSON-compatible dictionary."""
        return {
            "round_number": self.round_number,
            "turn_index": self.turn_index,
            "roll_mode": self.roll_mode,
            "combatants": [c.to_dict() for c in self.combatants],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Encounter:
        """Build an encounter from a dictionary loaded from JSON."""
        encounter = cls(
            combatants=[Combatant.from_dict(cd) for cd in data.get("combatants", [])],
            round_number=data.get("round_number", 1),
            turn_index=data.get("turn_index", 0),
            roll_mode=data.get("roll_mode", "auto"),
        )
        return encounter

    def save(self, filepath: str | Path) -> None:
        """Save the complete encounter state to a JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as json_file:
            json.dump(self.to_dict(), json_file, indent=2)

    @classmethod
    def load(cls, filepath: str | Path) -> Encounter:
        """Load an encounter that was previously saved as JSON."""
        path = Path(filepath)
        with path.open("r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        return cls.from_dict(data)


def run_encounter_console(
        encounter: Encounter,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        roller: Roller = DEFAULT_ROLLER,
) -> None:
    """Run the text-command loop used by the Dungeon Master."""
    output_func("\n" + "=" * 50)
    output_func("      DUNGEON MASTER ENCOUNTER MANAGER")
    output_func("=" * 50)

    # Initiative setup
    if not encounter.initiative_rolled:
        output_func("\nInitiative has not been rolled yet.")
        mode_choice = input_func(
            "Roll mode: [A]uto roll all, or [M]anual input? [A/m]: "
        ).strip().lower()
        if mode_choice == "m":
            encounter.roll_mode = "manual"
            manual_rolls: dict[str, int] = {}
            for combatant in encounter.combatants:
                dex_mod = combatant.modifier("dexterity")
                prompt = (
                    f"Enter initiative for {combatant.name} "
                    f"(DEX mod {dex_mod:+d}): "
                )
                while True:
                    value = input_func(prompt).strip()
                    try:
                        manual_rolls[combatant.name] = int(value)
                        break
                    except ValueError:
                        output_func("Please enter an integer.")
            encounter.roll_initiative(roller=roller, manual_rolls=manual_rolls)
        else:
            encounter.roll_mode = "auto"
            encounter.roll_initiative(roller=roller)
        output_func("\nInitiative rolled and turn order sorted!")

    output_func("\n" + encounter.status_table())
    output_func("\nType 'help' or '?' for available DM commands.")

    while True:
        status_msg = encounter.check_battle_status()
        if status_msg:
            output_func(f"\n*** {status_msg} ***")

        active = encounter.active_combatant
        if not active:
            output_func("No combatants remaining in encounter.")
            break

        # An unconscious player normally rolls a death save on their turn.
        needs_death_save = (
                not active.is_conscious
                and active.combatant_type == "player"
                and active.is_alive
                and not active.stable
        )
        if needs_death_save:
            output_func(
                f"\n[ALERT] {active.name} starts turn UNCONSCIOUS "
                f"(Death Saves: {active.death_saves_success}S / "
                f"{active.death_saves_failure}F)"
            )
            ds_choice = input_func("Roll death save now? (y/n): ").strip().lower()
            if ds_choice == "y":
                if encounter.roll_mode == "manual":
                    val = input_func(f"Enter {active.name}'s physical d20 roll: ").strip()
                    roll_val = int(val) if val.isdigit() else roller.randint(1, 20)
                else:
                    roll_val = roller.randint(1, 20)
                msg = active.record_death_save(roll_val)
                output_func(f"Death Save: {msg}")

        prompt = (
            f"\n[Round {encounter.round_number} | Turn: {active.name} "
            f"({active.hit_points}/{active.max_hit_points} HP)] > "
        )
        try:
            cmd_line = input_func(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            output_func("\nExiting encounter manager.")
            break

        if not cmd_line:
            continue

        parts = cmd_line.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in {"q", "quit", "exit"}:
            output_func("Combat encounter paused / ended.")
            break

        elif cmd in {"help", "?"}:
            output_func(
                "\nAvailable DM Commands:\n"
                "  n, next               Advance to the next turn\n"
                "  p, prev               Go back to the previous turn\n"
                "  s, status             Show encounter status table\n"
                "  a, attack [target]    Active combatant attacks target [adv|dis]\n"
                "  d, dmg <tgt> <amt>    Apply damage to target (e.g. 'd goblin 1 5 fire')\n"
                "  h, heal <tgt> <amt>   Restore HP to target (e.g. 'heal liam 6')\n"
                "  temp <tgt> <amt>      Grant temporary HP (e.g. 'temp liam 5')\n"
                "  save <tgt> <stat> <dc> Roll saving throw (e.g. 'save goblin1 dex 13')\n"
                "  cond add <tgt> <c>    Add condition (e.g. 'cond add goblin1 prone')\n"
                "  cond rem <tgt> <c>    Remove condition (e.g. 'cond rem goblin1 prone')\n"
                "  ds [target]           Roll or record a death saving throw\n"
                "  spawn <type> [count]  Spawn NPC reinforcements (e.g. 'spawn goblin 2')\n"
                "  remove <target>       Remove combatant from encounter\n"
                "  roll <expr>           Roll dice expression (e.g. 'roll 2d6+3')\n"
                "  mode [auto|manual]    Switch dice rolling mode\n"
                "  save-session [file]   Save encounter state to JSON\n"
                "  load-session [file]   Load encounter state from JSON\n"
            )

        elif cmd in {"s", "status"}:
            output_func("\n" + encounter.status_table())

        elif cmd in {"n", "next"}:
            next_c, advanced = encounter.next_turn()
            if advanced:
                output_func(f"\n--- Advanced to Round {encounter.round_number} ---")
            output_func(f"Next turn: {next_c.name if next_c else 'None'}")

        elif cmd in {"p", "prev"}:
            prev_c = encounter.prev_turn()
            output_func(f"Moved back to: {prev_c.name if prev_c else 'None'}")

        elif cmd in {"a", "attack"}:
            target = None
            adv = "adv" in [a.lower() for a in args]
            dis = "dis" in [a.lower() for a in args]
            clean_args = [a for a in args if a.lower() not in {"adv", "dis"}]
            if clean_args:
                target = encounter.find_combatant(" ".join(clean_args))

            if not target:
                valid_targets = [
                    combatant
                    for combatant in encounter.combatants
                    if combatant != active and combatant.is_alive
                ]
                if not valid_targets:
                    output_func("No valid targets available.")
                    continue
                output_func("Select target:")
                for number, valid_target in enumerate(valid_targets, start=1):
                    output_func(
                        f"  {number}. {valid_target.name} "
                        f"(AC {valid_target.armor_class}, "
                        f"HP {valid_target.hit_points}/"
                        f"{valid_target.max_hit_points})"
                    )
                choice = input_func("Target name or number: ").strip()
                target = encounter.find_combatant(choice)
                if not target and choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(valid_targets):
                        target = valid_targets[idx]

            if not target:
                output_func("Target not found.")
                continue

            manual_d20 = None
            if encounter.roll_mode == "manual":
                val = input_func(f"Enter physical d20 roll for {active.name}: ").strip()
                if val.isdigit():
                    manual_d20 = int(val)

            result = attack(
                active,
                target,
                advantage=adv,
                disadvantage=dis,
                roller=roller,
                manual_d20=manual_d20,
            )
            output_func("\n" + str(result))

            if (
                    result.hit
                    and encounter.roll_mode == "manual"
                    and manual_d20 is not None
            ):
                damage_input = input_func(
                    f"Damage dealt was {result.damage_dealt}. Override damage? "
                    "(leave blank to keep): "
                ).strip()
                if damage_input.isdigit():
                    override = int(damage_input)
                    difference = override - result.damage_dealt
                    target.hit_points = max(
                        0,
                        min(
                            target.max_hit_points,
                            target.hit_points - difference,
                        ),
                    )
                    output_func(
                        f"Updated {target.name} HP to {target.hit_points}/"
                        f"{target.max_hit_points}"
                    )

        elif cmd in {"d", "dmg", "damage"}:
            if len(args) < 2:
                output_func("Usage: damage <target> <amount> [damage_type]")
                continue
            amt_str = args[-1] if not args[-1].isalpha() else args[-2]
            type_str = args[-1] if args[-1].isalpha() else "untyped"
            target_name = " ".join(args[:-2] if args[-1].isalpha() else args[:-1])
            target = encounter.find_combatant(target_name)
            if not target:
                output_func(f"Combatant {target_name!r} not found.")
                continue
            try:
                amt = int(amt_str)
            except ValueError:
                output_func("Amount must be a whole number.")
                continue
            dealt = target.take_damage(amt, type_str)
            output_func(
                f"{target.name} took {dealt} {type_str} damage "
                f"(HP: {target.hit_points}/{target.max_hit_points})"
            )

        elif cmd in {"h", "heal"}:
            parsed = _read_target_and_amount(
                encounter,
                args,
                "Usage: heal <target> <amount>",
                output_func,
            )
            if parsed is None:
                continue
            target, amount = parsed
            restored = target.heal(amount)
            output_func(
                f"{target.name} healed for {restored} HP "
                f"(HP: {target.hit_points}/{target.max_hit_points})"
            )

        elif cmd in {"temp"}:
            parsed = _read_target_and_amount(
                encounter,
                args,
                "Usage: temp <target> <amount>",
                output_func,
            )
            if parsed is None:
                continue
            target, amount = parsed
            target.set_temp_hp(amount)
            output_func(f"{target.name} now has {target.temp_hp} temporary HP.")

        elif cmd in {"save"}:
            if len(args) < 3:
                output_func("Usage: save <target> <ability> <dc> [adv|dis]")
                continue
            adv = "adv" in [a.lower() for a in args]
            dis = "dis" in [a.lower() for a in args]
            clean = [a for a in args if a.lower() not in {"adv", "dis"}]
            dc_val = int(clean[-1])
            ability_name = clean[-2]
            target_name = " ".join(clean[:-2])
            target = _find_target(encounter, target_name, output_func)
            if target is None:
                continue
            manual_roll = _read_manual_d20(encounter, target, input_func)
            passed, total, nat = make_saving_throw(
                target,
                ability_name,
                dc_val,
                advantage=adv,
                disadvantage=dis,
                roller=roller,
                manual_roll=manual_roll,
            )
            result_str = "SUCCESS" if passed else "FAILURE"
            output_func(
                f"{target.name} {ability_name.upper()} Save: d20 ({nat}) "
                f"= {total} vs DC {dc_val} -> {result_str}"
            )

        elif cmd in {"cond"}:
            if len(args) < 3 or args[0].lower() not in {"add", "rem", "remove"}:
                output_func("Usage: cond <add|rem> <target> <condition>")
                continue
            action = args[0].lower()
            cond_name = args[-1].lower()
            target_name = " ".join(args[1:-1])
            target = encounter.find_combatant(target_name)
            if not target:
                output_func(f"Combatant {target_name!r} not found.")
                continue
            if action == "add":
                target.add_condition(cond_name)
                output_func(f"Added condition '{cond_name}' to {target.name}.")
            else:
                target.remove_condition(cond_name)
                output_func(f"Removed condition '{cond_name}' from {target.name}.")

        elif cmd in {"ds"}:
            target_name = " ".join(args) if args else active.name
            target = _find_target(encounter, target_name, output_func)
            if target is None:
                continue
            manual_roll = _read_manual_d20(encounter, target, input_func)
            roll_val = manual_roll if manual_roll is not None else roller.randint(1, 20)
            res = target.record_death_save(roll_val)
            output_func(f"Death Save: {res}")

        elif cmd in {"spawn"}:
            if not args:
                choices = ", ".join(sorted(get_available_monsters()))
                output_func(f"Available monsters: {choices}")
                output_func("Usage: spawn <monster_type> [count]")
                continue
            m_type = args[0].lower()
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
            available = get_available_monsters()
            if m_type not in available:
                choices = ", ".join(sorted(available))
                output_func(
                    f"Unknown monster {m_type!r}. Available: {choices}"
                )
                continue
            for _ in range(count):
                existing_count = sum(
                    1
                    for combatant in encounter.combatants
                    if combatant.monster_type == m_type
                )
                disp_name = f"{available[m_type].name} {existing_count + 1}"
                new_npc = create_monster(m_type, name=disp_name)
                if encounter.initiative_rolled:
                    dex_mod = new_npc.modifier("dexterity")
                    new_npc.initiative = roller.randint(1, 20) + dex_mod
                encounter.add_combatant(new_npc)
                output_func(
                    f"Spawned {disp_name} (Init {new_npc.initiative}, "
                    f"HP {new_npc.hit_points}, AC {new_npc.armor_class})"
                )

        elif cmd in {"remove"}:
            if not args:
                output_func("Usage: remove <target>")
                continue
            target_name = " ".join(args)
            removed = encounter.remove_combatant(target_name)
            if removed:
                output_func(f"Removed {removed.name} from combat.")
            else:
                output_func(f"Combatant {target_name!r} not found.")

        elif cmd in {"roll"}:
            if not args:
                output_func("Usage: roll <dice expression> (e.g. 'roll 2d6+3')")
                continue
            expr = "".join(args)
            try:
                rolls, total = roll_expression(expr, roller=roller)
                rolls_text = " + ".join(str(r) for r in rolls)
                output_func(f"Rolled {expr}: [{rolls_text}] = {total}")
            except ValueError as error:
                output_func(f"Error rolling dice: {error}")

        elif cmd in {"mode"}:
            if args and args[0].lower() in {"auto", "manual"}:
                encounter.roll_mode = args[0].lower()
            else:
                encounter.roll_mode = "manual" if encounter.roll_mode == "auto" else "auto"
            output_func(f"Dice roll mode set to: {encounter.roll_mode.upper()}")

        elif cmd in {"save-session"}:
            fname = args[0] if args else "active_session.json"
            if not fname.endswith(".json"):
                fname += ".json"
            path = ENCOUNTERS_DIRECTORY / fname
            encounter.save(path)
            output_func(f"Session saved to {path.name}")

        elif cmd in {"load-session"}:
            fname = args[0] if args else "active_session.json"
            if not fname.endswith(".json"):
                fname += ".json"
            path = ENCOUNTERS_DIRECTORY / fname
            if not path.exists():
                output_func(f"Save file {path} not found.")
                continue
            loaded = Encounter.load(path)
            encounter.combatants = loaded.combatants
            encounter.round_number = loaded.round_number
            encounter.turn_index = loaded.turn_index
            encounter.roll_mode = loaded.roll_mode
            encounter.initiative_rolled = loaded.initiative_rolled
            output_func(f"Loaded session from {path.name}!")
            output_func("\n" + encounter.status_table())

        else:
            output_func(f"Unknown command {cmd!r}. Type 'help' for a list of commands.")
