# D&D Encounter Manager & Combat Assistant

A modular combat runner and assistant designed for Dungeon Masters running local D&D 5e tabletop club sessions.

Run `main.py` to launch the interactive DM console. You can load characters from JSON sheets or class presets, spawn monsters from templates, track initiative and rounds, apply damage and healing, manage conditions and death saves, and persist encounter sessions.

## Project Structure

- `main.py` — public entry point and CLI runner
- `encounter.py` — round/turn manager, initiative tracking, and live interactive DM REPL
- `models.py` — `Combatant`, `Weapon`, and `AttackResult` data classes with health/status tracking
- `combat.py` — d20 attack rolls, crits, damage calculations, saving throws, and dice parsing
- `character_defaults.py` — player classes and weapons loader (from `data/`)
- `monster_defaults.py` — core monsters loader (from `data/`) and custom monster loader (from `monsters/`)
- `sheet_loader.py` — character-sheet discovery and JSON import
- `dm_setup.py` — interactive encounter setup prompt
- `data/` — human-editable JSON configuration files (`classes.json`, `monsters.json`, `weapons.json`)
- `monsters/*.json` — individual custom monster stat blocks (editable without changing code)
- `character_sheets/*.json` — saved player-character configurations
- `encounters/*.json` — saved active encounter states
- `test_main.py` — automated rules, loading, and encounter test suite

---

## Editing Classes, Monsters, and Weapons (No Code Required)

All presets have been extracted into human-editable JSON text files:

- **`data/classes.json`**: Starter presets for all 12 core classes (AC, hit dice, ability scores, proficiencies, starter weapon).
- **`data/weapons.json`**: Damage dice, damage types, associated ability (strength/dexterity), and ranged flags.
- **`data/monsters.json`**: Core monster statistics.
- **`monsters/*.json`**: Drop any individual `.json` monster file into the `monsters/` folder (e.g. `monsters/goblin_boss.json`, `bandit.json`, `zombie.json`). It will immediately be available to the DM without restarting Python!

### Example Custom Monster (`monsters/goblin_boss.json`)

```json
{
  "name": "Goblin Boss",
  "armor_class": 17,
  "hit_points": 21,
  "ability_scores": {
    "strength": 10,
    "dexterity": 14,
    "constitution": 10,
    "intelligence": 10,
    "wisdom": 8,
    "charisma": 10
  },
  "proficiency_bonus": 2,
  "weapon": "scimitar",
  "proficient_weapons": ["scimitar"],
  "resistances": [],
  "vulnerabilities": [],
  "immunities": []
}
```

---

## Live Encounter Console Commands

During active combat, the DM has a fast 1-line command prompt:

| Command | Shorthand | Description | Example |
| :--- | :--- | :--- | :--- |
| `next` | `n` | Advance turn (advances round when wrapping) | `next` |
| `prev` | `p` | Step back a turn | `prev` |
| `status` | `s` | Display initiative and health summary table | `status` |
| `attack` | `a` | Active combatant attacks target `[adv\|dis]` | `attack goblin1 adv` |
| `damage` | `d` | Deal damage (absorbs temp HP first, applies defenses) | `damage orc 1 8 slashing` |
| `heal` | `h` | Restore HP (capped at max HP, wakes up downed PCs) | `heal liam 6` |
| `temp` | — | Grant temporary HP | `temp liam 5` |
| `save` | — | Roll an ability saving throw vs DC | `save goblin 1 dex 13` |
| `cond add` | — | Add condition (`prone`, `blinded`, `poisoned`, etc.) | `cond add goblin 1 prone` |
| `cond rem` | — | Remove condition | `cond rem goblin 1 prone` |
| `ds` | — | Roll or input a death save for a downed PC | `ds liam` |
| `spawn` | — | Spawn reinforcements mid-battle | `spawn goblin 2` |
| `remove` | — | Remove a combatant from the encounter | `remove orc 1` |
| `roll` | — | Roll arbitrary dice expression | `roll 2d6+3` or `roll d20` |
| `mode` | — | Switch between automated rolls and physical table rolls | `mode manual` |
| `save-session` | — | Save active encounter state to JSON | `save-session encounter1` |
| `load-session` | — | Resume a saved encounter session | `load-session encounter1` |
| `quit` | `q` | Exit the encounter console | `quit` |

---

## 5e Rules Supported

1. **Initiative**: Rolled automatically or input manually (`d20 + DEX mod`), sorted with DEX tie-breakers.
2. **Health & Temp HP**: Enforces `max_hit_points`, non-stacking `temp_hp` damage absorption, and healing limits.
3. **Player Downed & Death Saves**:
   - Dropping to 0 HP adds `[UNCONSCIOUS]`.
   - Death saves tracked: 10+ is success, <10 is failure, natural 1 gives 2 failures, natural 20 regains 1 HP.
   - 3 successes stabilizes the PC; 3 failures or massive damage marks them dead.
   - Taking damage at 0 HP inflicts death save failure (2 if critical).
4. **Conditions**:
   - `prone`, `blinded`, `poisoned`, `stunned`, `paralyzed`, `unconscious`, `restrained`, `dodging`.
   - Attacks automatically factor in conditions (e.g. melee advantage against prone/unconscious, auto-crit on hits against paralyzed/unconscious targets within melee range).
5. **Physical / Hybrid Play**: Toggle `mode manual` at any time so players rolling physical dice at the club table can enter their exact d20 and damage rolls.

---

## Running the Automated Test Suite

```bash
python -m unittest test_main.py
```
