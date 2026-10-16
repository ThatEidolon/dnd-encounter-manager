"""Roll dice and resolve D&D 5e-style attacks and saving throws.

Most functions accept a ``roller`` argument.  The real game uses Python's
random-number generator, while tests provide predictable rolls.  This pattern
is called dependency injection.
"""

from __future__ import annotations

import random
import re
from typing import Protocol

from models import AttackResult, Combatant, Weapon


class Roller(Protocol):
    """Describe any object capable of producing a random integer."""

    def randint(self, start: int, end: int) -> int:
        """Return an integer between ``start`` and ``end``."""
        ...


class _RandomRoller:
    """Adapt Python's random module to the small ``Roller`` interface."""

    def __init__(self) -> None:
        self._generator = random.Random()

    def randint(self, start: int, end: int) -> int:
        """Return a random integer between the two endpoints."""
        return self._generator.randint(start, end)


_DICE_PATTERN = re.compile(r"^(\d*)d(\d+)$", re.IGNORECASE)
_EXPR_PATTERN = re.compile(r"^(\d*)d(\d+)(?:\s*([+-])\s*(\d+))?$", re.IGNORECASE)
DEFAULT_ROLLER: Roller = _RandomRoller()


def ability_modifier(score: int) -> int:
    """Convert an ability score into its D&D ability modifier."""
    if not 1 <= score <= 30:
        raise ValueError("An ability score must be between 1 and 30")
    return (score - 10) // 2


def roll_dice(expression: str, roller: Roller = DEFAULT_ROLLER) -> tuple[int, ...]:
    """Roll a simple expression such as ``d20`` or ``2d6``."""
    match = _DICE_PATTERN.fullmatch(expression.strip())
    if not match:
        raise ValueError(f"Invalid dice expression: {expression!r}")
    count_str, sides_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    if count < 1 or sides < 2:
        raise ValueError("Dice require at least one die with at least two sides")
    return tuple(roller.randint(1, sides) for _ in range(count))


def roll_expression(
        expression: str,
        roller: Roller = DEFAULT_ROLLER,
) -> tuple[tuple[int, ...], int]:
    """Roll dice plus an optional modifier, such as ``2d6+3``."""
    match = _EXPR_PATTERN.fullmatch(expression.strip())
    if not match:
        raise ValueError(f"Invalid dice expression: {expression!r}")
    count_str, sides_str, sign, mod_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    modifier = int(mod_str) if mod_str else 0
    if sign == "-":
        modifier = -modifier
    if count < 1 or sides < 2:
        raise ValueError("Dice require at least one die with at least two sides")
    rolls = tuple(roller.randint(1, sides) for _ in range(count))
    return rolls, sum(rolls) + modifier


def _roll_d20(
        roller: Roller = DEFAULT_ROLLER,
        *,
        advantage: bool = False,
        disadvantage: bool = False,
        manual_roll: int | None = None,
) -> tuple[tuple[int, ...], int]:
    """Roll a d20, applying advantage, disadvantage, or a manual roll."""
    if manual_roll is not None:
        return (manual_roll,), manual_roll
    if advantage == disadvantage:
        roll = roller.randint(1, 20)
        return (roll,), roll
    rolls = (roller.randint(1, 20), roller.randint(1, 20))
    return rolls, max(rolls) if advantage else min(rolls)


def calculate_damage(
        weapon: Weapon,
        ability_mod: int,
        *,
        critical: bool = False,
        damage_bonus: int = 0,
        roller: Roller = DEFAULT_ROLLER,
        manual_rolls: tuple[int, ...] | None = None,
) -> tuple[tuple[int, ...], int]:
    """Roll a weapon's damage dice and add its flat modifiers."""
    if manual_rolls is not None:
        rolls = manual_rolls
    else:
        match = _DICE_PATTERN.fullmatch(weapon.damage_dice.strip())
        if not match:
            raise ValueError(f"Invalid weapon damage dice: {weapon.damage_dice!r}")
        count_str, sides_str = match.groups()
        count = int(count_str) if count_str else 1
        sides = int(sides_str)
        dice = f"{count * (2 if critical else 1)}d{sides}"
        rolls = roll_dice(dice, roller)
    return rolls, max(0, sum(rolls) + ability_mod + damage_bonus)


def attack(
        attacker: Combatant,
        target: Combatant,
        weapon: Weapon | None = None,
        *,
        advantage: bool = False,
        disadvantage: bool = False,
        attack_bonus: int = 0,
        damage_bonus: int = 0,
        roller: Roller = DEFAULT_ROLLER,
        manual_d20: int | None = None,
        manual_damage_rolls: tuple[int, ...] | None = None,
        is_melee: bool = True,
) -> AttackResult:
    """Resolve one attack, change the target's HP, and return the details."""
    weapon = weapon or attacker.wielded_weapon
    if weapon is None:
        raise ValueError(
            f"{attacker.name} has no wielded weapon; equip one or pass a weapon to attack()"
        )

    # Conditions can add advantage or disadvantage to the attack roll.
    effective_adv = advantage
    effective_dis = disadvantage

    if "blinded" in attacker.conditions or "poisoned" in attacker.conditions:
        effective_dis = True
    advantage_conditions = {
        "blinded",
        "restrained",
        "stunned",
        "paralyzed",
        "unconscious",
    }
    if target.conditions.intersection(advantage_conditions):
        effective_adv = True
    if "prone" in target.conditions:
        if is_melee and not weapon.is_ranged:
            effective_adv = True
        else:
            effective_dis = True
    if "dodging" in target.conditions:
        effective_dis = True

    ability_mod = attacker.modifier(weapon.ability)
    proficiency = (
        attacker.proficiency_bonus
        if weapon.name.lower() in {name.lower() for name in attacker.proficient_weapons}
        else 0
    )
    attack_modifier = ability_mod + proficiency + attack_bonus
    d20_rolls, natural_roll = _roll_d20(
        roller,
        advantage=effective_adv,
        disadvantage=effective_dis,
        manual_roll=manual_d20,
    )
    attack_total = natural_roll + attack_modifier
    critical = natural_roll == 20
    hit = natural_roll != 1 and (critical or attack_total >= target.armor_class)

    # A nearby hit against an unconscious or paralyzed target is critical.
    helpless_conditions = {"unconscious", "paralyzed"}
    if (
            hit
            and is_melee
            and not weapon.is_ranged
            and target.conditions.intersection(helpless_conditions)
    ):
        critical = True

    damage_rolls: tuple[int, ...] = ()
    rolled_damage = damage_dealt = 0
    if hit:
        damage_rolls, rolled_damage = calculate_damage(
            weapon,
            ability_mod,
            critical=critical,
            damage_bonus=damage_bonus,
            roller=roller,
            manual_rolls=manual_damage_rolls,
        )
        damage_dealt = target.take_damage(rolled_damage, weapon.damage_type, is_critical=critical)

    return AttackResult(
        attacker=attacker,
        target=target,
        weapon=weapon.name,
        d20_rolls=d20_rolls,
        natural_roll=natural_roll,
        attack_modifier=attack_modifier,
        attack_total=attack_total,
        target_ac=target.armor_class,
        hit=hit,
        critical=critical,
        damage_rolls=damage_rolls,
        damage_modifier=ability_mod + damage_bonus,
        rolled_damage=rolled_damage,
        damage_dealt=damage_dealt,
        target_hit_points=target.hit_points,
    )


def make_saving_throw(
        combatant: Combatant,
        ability: str,
        dc: int,
        *,
        advantage: bool = False,
        disadvantage: bool = False,
        roller: Roller = DEFAULT_ROLLER,
        manual_roll: int | None = None,
) -> tuple[bool, int, int]:
    """Roll a saving throw and return passed, total, and natural roll."""
    ability_key = ability.lower().strip()
    ability_mod = combatant.modifier(ability_key)
    prof = (
        combatant.proficiency_bonus
        if ability_key in {s.lower() for s in combatant.saving_throw_proficiencies}
        else 0
    )
    mod = ability_mod + prof
    _, nat_roll = _roll_d20(
        roller,
        advantage=advantage,
        disadvantage=disadvantage,
        manual_roll=manual_roll,
    )
    total = nat_roll + mod
    passed = total >= dc
    return passed, total, nat_roll
