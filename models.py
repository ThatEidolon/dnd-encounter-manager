"""Core data models shared by combat, characters, monsters, and loaders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Weapon:
    name: str
    damage_dice: str
    damage_type: str
    ability: str = "strength"
    is_ranged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "damage_dice": self.damage_dice,
            "damage_type": self.damage_type,
            "ability": self.ability,
            "is_ranged": self.is_ranged,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Weapon:
        return cls(
            name=data["name"],
            damage_dice=data["damage_dice"],
            damage_type=data["damage_type"],
            ability=data.get("ability", "strength"),
            is_ranged=data.get("is_ranged", False),
        )


DEFAULT_WEAPON = Weapon("shortsword", "1d6", "piercing", ability="dexterity")


@dataclass(frozen=True)
class CharacterClassDefaults:
    """A ready-to-play level-one build for a core 5e character class."""

    name: str
    hit_die: int
    armor_class: int
    ability_scores: tuple[tuple[str, int], ...]
    saving_throws: frozenset[str]
    starter_weapon: str


@dataclass(frozen=True)
class MonsterDefaults:
    """Reusable statistics for one kind of NPC or monster."""

    name: str
    armor_class: int
    hit_points: int
    ability_scores: tuple[tuple[str, int], ...]
    proficiency_bonus: int
    weapon: str
    proficient_weapons: frozenset[str]
    resistances: frozenset[str] = frozenset()
    vulnerabilities: frozenset[str] = frozenset()
    immunities: frozenset[str] = frozenset()


@dataclass
class Combatant:
    name: str
    armor_class: int
    hit_points: int
    ability_scores: dict[str, int]
    combatant_type: str = "npc"
    character_class: str | None = None
    monster_type: str | None = None
    level: int = 1
    hit_die: int | None = None
    wielded_weapon: Weapon | None = field(default_factory=lambda: DEFAULT_WEAPON)
    proficiency_bonus: int = 2
    proficient_weapons: set[str] = field(default_factory=set)
    saving_throw_proficiencies: set[str] = field(default_factory=set)
    resistances: set[str] = field(default_factory=set)
    vulnerabilities: set[str] = field(default_factory=set)
    immunities: set[str] = field(default_factory=set)
    max_hit_points: int = 0
    temp_hp: int = 0
    initiative: int = 0
    conditions: set[str] = field(default_factory=set)
    death_saves_success: int = 0
    death_saves_failure: int = 0
    stable: bool = False

    def __post_init__(self) -> None:
        self.combatant_type = self.combatant_type.lower()
        if self.combatant_type not in {"player", "npc"}:
            raise ValueError("combatant_type must be 'player' or 'npc'")
        if self.armor_class < 0:
            raise ValueError("armor_class cannot be negative")
        if self.hit_points < 0:
            raise ValueError("hit_points cannot be negative")
        if self.max_hit_points <= 0:
            self.max_hit_points = self.hit_points
        self.conditions = {c.lower() for c in self.conditions}

    @classmethod
    def from_player_class(
        cls,
        name: str,
        class_type: str,
        **overrides: Any,
    ) -> Combatant:
        """Create a level-one player using a class starter preset."""
        from character_defaults import create_player_character

        return create_player_character(name, class_type, **overrides)

    @classmethod
    def from_monster(
        cls,
        monster_type: str,
        *,
        name: str | None = None,
    ) -> Combatant:
        """Create an NPC using a monster preset."""
        from monster_defaults import create_monster

        return create_monster(monster_type, name=name)

    @property
    def is_conscious(self) -> bool:
        return self.hit_points > 0 and "unconscious" not in self.conditions

    @property
    def is_alive(self) -> bool:
        if self.combatant_type == "player":
            return self.death_saves_failure < 3 and "dead" not in self.conditions
        return self.hit_points > 0 and "dead" not in self.conditions

    def modifier(self, ability: str) -> int:
        from combat import ability_modifier

        try:
            score = self.ability_scores[ability.lower()]
        except KeyError as error:
            raise ValueError(f"{self.name} has no {ability!r} ability score") from error
        return ability_modifier(score)

    def heal(self, amount: int) -> int:
        """Restore hit points up to max_hit_points. Wakes up unconscious combatants."""
        if amount <= 0 or not self.is_alive:
            return 0
        if self.hit_points == 0:
            self.death_saves_success = 0
            self.death_saves_failure = 0
            self.stable = False
            self.conditions.discard("unconscious")
        previous = self.hit_points
        self.hit_points = min(self.max_hit_points, self.hit_points + amount)
        return self.hit_points - previous

    def set_temp_hp(self, amount: int) -> int:
        """Apply temporary HP according to 5e rules (does not stack, takes highest)."""
        amount = max(0, amount)
        self.temp_hp = max(self.temp_hp, amount)
        return self.temp_hp

    def take_damage(
        self,
        amount: int,
        damage_type: str = "untyped",
        *,
        is_critical: bool = False,
    ) -> int:
        """Apply defenses, reduce temp/regular HP, handle 5e death rules, and return damage dealt."""
        damage_type = damage_type.lower()
        if damage_type in self.immunities:
            amount = 0
        else:
            resistant = damage_type in self.resistances
            vulnerable = damage_type in self.vulnerabilities
            if resistant and not vulnerable:
                amount //= 2
            elif vulnerable and not resistant:
                amount *= 2

        amount = max(0, amount)
        if amount == 0:
            return 0

        # If already at 0 HP
        if self.hit_points == 0:
            if self.combatant_type == "player" and self.is_alive:
                fails = 2 if is_critical else 1
                self.death_saves_failure += fails
                self.stable = False
                if amount >= self.max_hit_points or self.death_saves_failure >= 3:
                    self.death_saves_failure = 3
                    self.conditions.add("dead")
            return amount

        # Absorb damage through temporary hit points first
        if self.temp_hp > 0:
            absorbed = min(self.temp_hp, amount)
            self.temp_hp -= absorbed
            damage_to_hp = amount - absorbed
        else:
            damage_to_hp = amount

        if damage_to_hp > 0:
            if damage_to_hp >= self.hit_points:
                overkill = damage_to_hp - self.hit_points
                self.hit_points = 0
                if self.combatant_type == "player":
                    self.conditions.add("unconscious")
                    self.stable = False
                    if overkill >= self.max_hit_points:
                        self.death_saves_failure = 3
                        self.conditions.add("dead")
                else:
                    self.conditions.add("dead")
            else:
                self.hit_points -= damage_to_hp

        return amount

    def record_death_save(self, roll: int) -> str:
        """Record the result of a death saving throw for a downed player."""
        if not self.is_alive:
            return f"{self.name} is dead."
        if self.hit_points > 0:
            return f"{self.name} is conscious (HP: {self.hit_points})."

        if roll == 20:
            self.hit_points = 1
            self.death_saves_success = 0
            self.death_saves_failure = 0
            self.stable = False
            self.conditions.discard("unconscious")
            return f"{self.name} rolled a natural 20 and regained 1 HP!"
        elif roll == 1:
            self.death_saves_failure += 2
            self.stable = False
            if self.death_saves_failure >= 3:
                self.conditions.add("dead")
                return f"{self.name} rolled a natural 1 (2 failures) and has died!"
            return f"{self.name} rolled a 1 (2 failures: {self.death_saves_failure}/3)."
        elif roll >= 10:
            self.death_saves_success += 1
            if self.death_saves_success >= 3:
                self.stable = True
                self.death_saves_success = 0
                self.death_saves_failure = 0
                return f"{self.name} rolled {roll} (3 successes) and is now stabilized!"
            return f"{self.name} rolled {roll} (success: {self.death_saves_success}/3)."
        else:
            self.death_saves_failure += 1
            self.stable = False
            if self.death_saves_failure >= 3:
                self.conditions.add("dead")
                return f"{self.name} rolled {roll} (3 failures) and has died!"
            return f"{self.name} rolled {roll} (failure: {self.death_saves_failure}/3)."

    def add_condition(self, condition: str) -> None:
        self.conditions.add(condition.strip().lower())

    def remove_condition(self, condition: str) -> None:
        self.conditions.discard(condition.strip().lower())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "armor_class": self.armor_class,
            "hit_points": self.hit_points,
            "max_hit_points": self.max_hit_points,
            "temp_hp": self.temp_hp,
            "ability_scores": dict(self.ability_scores),
            "combatant_type": self.combatant_type,
            "character_class": self.character_class,
            "monster_type": self.monster_type,
            "level": self.level,
            "hit_die": self.hit_die,
            "wielded_weapon": self.wielded_weapon.to_dict() if self.wielded_weapon else None,
            "proficiency_bonus": self.proficiency_bonus,
            "proficient_weapons": sorted(self.proficient_weapons),
            "saving_throw_proficiencies": sorted(self.saving_throw_proficiencies),
            "resistances": sorted(self.resistances),
            "vulnerabilities": sorted(self.vulnerabilities),
            "immunities": sorted(self.immunities),
            "initiative": self.initiative,
            "conditions": sorted(self.conditions),
            "death_saves_success": self.death_saves_success,
            "death_saves_failure": self.death_saves_failure,
            "stable": self.stable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Combatant:
        weapon_data = data.get("wielded_weapon")
        weapon = Weapon.from_dict(weapon_data) if weapon_data else None
        combatant = cls(
            name=data["name"],
            armor_class=data["armor_class"],
            hit_points=data["hit_points"],
            ability_scores=data["ability_scores"],
            combatant_type=data.get("combatant_type", "npc"),
            character_class=data.get("character_class"),
            monster_type=data.get("monster_type"),
            level=data.get("level", 1),
            hit_die=data.get("hit_die"),
            wielded_weapon=weapon,
            proficiency_bonus=data.get("proficiency_bonus", 2),
            proficient_weapons=set(data.get("proficient_weapons", [])),
            saving_throw_proficiencies=set(data.get("saving_throw_proficiencies", [])),
            resistances=set(data.get("resistances", [])),
            vulnerabilities=set(data.get("vulnerabilities", [])),
            immunities=set(data.get("immunities", [])),
            max_hit_points=data.get("max_hit_points", data["hit_points"]),
            temp_hp=data.get("temp_hp", 0),
            initiative=data.get("initiative", 0),
            conditions=set(data.get("conditions", [])),
            death_saves_success=data.get("death_saves_success", 0),
            death_saves_failure=data.get("death_saves_failure", 0),
            stable=data.get("stable", False),
        )
        return combatant


@dataclass(frozen=True)
class AttackResult:
    attacker: Combatant
    target: Combatant
    weapon: str
    d20_rolls: tuple[int, ...]
    natural_roll: int
    attack_modifier: int
    attack_total: int
    target_ac: int
    hit: bool
    critical: bool
    damage_rolls: tuple[int, ...] = ()
    damage_modifier: int = 0
    rolled_damage: int = 0
    damage_dealt: int = 0
    target_hit_points: int = 0

    def __str__(self) -> str:
        roll_text = "/".join(str(roll) for roll in self.d20_rolls)
        if not self.hit:
            return (
                f"{self.attacker.name} attacks {self.target.name} with {self.weapon}: "
                f"d20 {roll_text} + {self.attack_modifier} = {self.attack_total}; miss."
            )
        critical_text = " critical hit" if self.critical else " hit"
        return (
            f"{self.attacker.name} attacks {self.target.name} with {self.weapon}: "
            f"d20 {roll_text} + {self.attack_modifier} = {self.attack_total};"
            f"{critical_text} for {self.damage_dealt} damage "
            f"({self.target_hit_points} HP remaining)."
        )
