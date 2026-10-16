import tempfile
import unittest
from pathlib import Path

from main import (
    MONSTERS,
    Combatant,
    Encounter,
    WEAPONS,
    ability_modifier,
    attack,
    create_monster,
    get_available_monsters,
    list_character_sheets,
    load_character_sheet_by_name,
    make_saving_throw,
    roll_expression,
    setup_combat,
)


class FixedRoller:
    def __init__(self, *rolls: int):
        self.rolls = iter(rolls)

    def randint(self, start: int, end: int) -> int:
        roll = next(self.rolls)
        if not start <= roll <= end:
            raise AssertionError(f"Fixed roll {roll} is outside {start}..{end}")
        return roll


def fighter(*, hp: int = 20, ac: int = 15) -> Combatant:
    return Combatant(
        name="Fighter",
        armor_class=ac,
        hit_points=hp,
        ability_scores={"strength": 16, "dexterity": 12},
        combatant_type="player",
        wielded_weapon=WEAPONS["sword"],
        proficiency_bonus=2,
        proficient_weapons={"sword"},
    )


class CombatRulesTests(unittest.TestCase):
    def test_monster_factory_applies_goblin_defaults(self):
        goblin = create_monster("goblin")

        self.assertEqual(goblin.monster_type, "goblin")
        self.assertEqual(goblin.armor_class, 15)
        self.assertEqual(goblin.hit_points, 7)
        self.assertEqual(goblin.wielded_weapon, WEAPONS["scimitar"])
        self.assertIn("scimitar", goblin.proficient_weapons)

    def test_character_sheet_can_be_discovered_and_loaded(self):
        self.assertIn("liam.json", {path.name for path in list_character_sheets()})

        liam = load_character_sheet_by_name("liam")

        self.assertEqual(liam.name, "Liam")
        self.assertEqual(liam.character_class, "fighter")
        self.assertEqual(liam.ability_scores["strength"], 16)

    def test_dm_setup_imports_players_and_creates_typed_npcs(self):
        answers = iter(["1", "liam", "2", "goblin", "orc"])
        messages: list[str] = []

        setup = setup_combat(lambda _prompt: next(answers), messages.append)

        self.assertEqual([player.name for player in setup.players], ["Liam"])
        self.assertEqual(
            [npc.monster_type for npc in setup.npcs], ["goblin", "orc"]
        )
        self.assertEqual(set(MONSTERS), {"goblin", "orc", "skeleton", "wolf", "ogre"})

    def test_directly_created_combatant_gets_a_default_weapon(self):
        goblin = Combatant(
            name="Goblin",
            armor_class=15,
            hit_points=7,
            ability_scores={"strength": 8, "dexterity": 14},
        )

        self.assertIs(goblin.wielded_weapon, WEAPONS["shortsword"])
        result = attack(goblin, fighter(), roller=FixedRoller(15, 4))
        self.assertEqual(result.weapon, "shortsword")

    def test_player_class_factory_applies_level_one_fighter_defaults(self):
        liam = Combatant.from_player_class("Liam", "Fighter")

        self.assertEqual(liam.character_class, "fighter")
        self.assertEqual(liam.combatant_type, "player")
        self.assertEqual(liam.level, 1)
        self.assertEqual(liam.hit_die, 10)
        self.assertEqual(liam.hit_points, 12)
        self.assertEqual(liam.armor_class, 18)
        self.assertEqual(liam.wielded_weapon, WEAPONS["longsword"])
        self.assertEqual(liam.saving_throw_proficiencies, {"strength", "constitution"})

    def test_attack_uses_the_attackers_wielded_weapon(self):
        attacker = fighter()
        target = fighter()
        target.combatant_type = "npc"

        result = attack(attacker, target, roller=FixedRoller(15, 4))

        self.assertEqual(attacker.combatant_type, "player")
        self.assertIs(attacker.wielded_weapon, WEAPONS["sword"])
        self.assertEqual(result.weapon, "sword")

    def test_ability_modifiers_round_down(self):
        self.assertEqual(ability_modifier(9), -1)
        self.assertEqual(ability_modifier(10), 0)
        self.assertEqual(ability_modifier(16), 3)

    def test_natural_one_misses_even_when_total_reaches_ac(self):
        attacker = fighter()
        target = fighter(ac=1)
        result = attack(attacker, target, WEAPONS["sword"], roller=FixedRoller(1))
        self.assertFalse(result.hit)
        self.assertIs(result.attacker, attacker)
        self.assertIs(result.target, target)

    def test_natural_twenty_hits_and_doubles_only_damage_dice(self):
        target = fighter(hp=30, ac=30)
        result = attack(
            fighter(), target, WEAPONS["sword"], roller=FixedRoller(20, 4, 5)
        )
        self.assertTrue(result.critical)
        self.assertEqual(result.damage_rolls, (4, 5))
        self.assertEqual(result.damage_dealt, 12)

    def test_advantage_uses_higher_d20(self):
        result = attack(
            fighter(), fighter(ac=15), WEAPONS["sword"],
            advantage=True, roller=FixedRoller(4, 12, 3),
        )
        self.assertEqual(result.natural_roll, 12)
        self.assertTrue(result.hit)

    def test_resistance_halves_damage_rounding_down(self):
        target = fighter(hp=20)
        target.resistances.add("slashing")
        result = attack(
            fighter(), target, WEAPONS["sword"], roller=FixedRoller(15, 4)
        )
        self.assertEqual(result.rolled_damage, 7)
        self.assertEqual(result.damage_dealt, 3)
        self.assertEqual(target.hit_points, 17)

    # --- New Tests for Health, Temp HP, Death Saves, Encounter, and Defaults ---

    def test_temp_hp_absorbs_damage_first(self):
        hero = fighter(hp=20)
        hero.set_temp_hp(8)
        self.assertEqual(hero.temp_hp, 8)

        dealt = hero.take_damage(5, "slashing")
        self.assertEqual(dealt, 5)
        self.assertEqual(hero.temp_hp, 3)
        self.assertEqual(hero.hit_points, 20)

        hero.take_damage(6, "slashing")
        self.assertEqual(hero.temp_hp, 0)
        self.assertEqual(hero.hit_points, 17)

    def test_heal_caps_at_max_hit_points(self):
        hero = fighter(hp=20)
        hero.take_damage(10)
        self.assertEqual(hero.hit_points, 10)

        restored = hero.heal(15)
        self.assertEqual(restored, 10)
        self.assertEqual(hero.hit_points, 20)

    def test_player_death_saves_and_recovery(self):
        hero = fighter(hp=10)
        hero.take_damage(10)
        self.assertEqual(hero.hit_points, 0)
        self.assertIn("unconscious", hero.conditions)

        # Roll 12: 1 success
        msg = hero.record_death_save(12)
        self.assertEqual(hero.death_saves_success, 1)

        # Roll 4: 1 failure
        hero.record_death_save(4)
        self.assertEqual(hero.death_saves_failure, 1)

        # Roll 20: regains 1 HP and wakes up
        hero.record_death_save(20)
        self.assertEqual(hero.hit_points, 1)
        self.assertNotIn("unconscious", hero.conditions)
        self.assertEqual(hero.death_saves_success, 0)
        self.assertEqual(hero.death_saves_failure, 0)

    def test_saving_throw_with_proficiency(self):
        hero = fighter()
        hero.saving_throw_proficiencies.add("strength")
        # hero has STR 16 (mod +3) and prof bonus +2 = +5 total
        passed, total, nat = make_saving_throw(hero, "strength", 15, roller=FixedRoller(10))
        self.assertEqual(nat, 10)
        self.assertEqual(total, 15)
        self.assertTrue(passed)

    def test_conditions_affect_attacks(self):
        attacker = fighter()
        defender = fighter(ac=15)
        defender.add_condition("prone")

        # Melee attack against prone defender gains advantage
        result = attack(attacker, defender, roller=FixedRoller(5, 16, 4))
        self.assertEqual(result.natural_roll, 16)
        self.assertTrue(result.hit)

    def test_encounter_turn_order_and_rounds(self):
        p1 = fighter(hp=20)
        p1.name = "Hero"
        p1.initiative = 18

        m1 = create_monster("goblin", name="Goblin 1")
        m1.initiative = 12

        encounter = Encounter([m1, p1])
        encounter.sort_by_initiative()

        self.assertEqual(encounter.active_combatant.name, "Hero")
        next_c, advanced = encounter.next_turn()
        self.assertEqual(next_c.name, "Goblin 1")
        self.assertFalse(advanced)

        next_c, advanced = encounter.next_turn()
        self.assertEqual(next_c.name, "Hero")
        self.assertTrue(advanced)
        self.assertEqual(encounter.round_number, 2)

    def test_custom_monsters_loaded_from_directory(self):
        available = get_available_monsters()
        self.assertIn("goblin_boss", available)
        boss = create_monster("goblin_boss")
        self.assertEqual(boss.name, "Goblin Boss")
        self.assertEqual(boss.armor_class, 17)

    def test_dice_expression_rolling(self):
        rolls, total = roll_expression("2d6+3", roller=FixedRoller(4, 5))
        self.assertEqual(rolls, (4, 5))
        self.assertEqual(total, 12)

    def test_encounter_save_and_load(self):
        p = fighter(hp=18)
        p.name = "Thorin"
        encounter = Encounter([p], round_number=3, turn_index=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_session.json"
            encounter.save(path)

            loaded = Encounter.load(path)
            self.assertEqual(loaded.round_number, 3)
            self.assertEqual(len(loaded.combatants), 1)
            self.assertEqual(loaded.combatants[0].name, "Thorin")


if __name__ == "__main__":
    unittest.main()
