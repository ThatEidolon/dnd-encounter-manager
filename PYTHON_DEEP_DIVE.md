# Python Deep Dive for the D&D Encounter Manager

This guide explains the Python features that may look unusual to a new
programmer. Read it after the main [Learning Guide](LEARNING_GUIDE.md), or jump
directly to a section when you meet unfamiliar syntax.

## 1. Decorators

A decorator changes or extends a class or function. It starts with `@` and is
written immediately above the thing it decorates:

```python
@dataclass
class Combatant:
    name: str
    hit_points: int
```

You can think of a decorator as passing the class or function into another
function. This simplified code shows the idea:

```python
class Combatant:
    ...

Combatant = dataclass(Combatant)
```

The project uses three kinds of decorators.

### `@dataclass`

`@dataclass` is a class decorator. It examines annotated attributes and creates
common methods automatically. For example, Python generates an `__init__()`
method, so this works without writing the initializer ourselves:

```python
sword = Weapon(
    name="longsword",
    damage_dice="1d8",
    damage_type="slashing",
)
```

Some project classes use `@dataclass(frozen=True)`. The parentheses pass an
option to the decorator. `frozen=True` prevents fields from being reassigned
after creation. That is useful for a `Weapon`, because one shared longsword
definition should not suddenly change its damage die.

`Combatant` is not frozen because its hit points and conditions must change
during battle.

The `field(default_factory=set)` calls in `Combatant` create a new empty set for
every combatant. Writing `conditions=set()` directly as a field default would
risk sharing one mutable set among multiple objects.

### `@classmethod`

A normal instance method receives `self`, the particular object being used. A
class method receives `cls`, the class itself:

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Combatant:
    return cls(
        name=data["name"],
        armor_class=data["armor_class"],
        hit_points=data["hit_points"],
        ability_scores=data["ability_scores"],
    )
```

Class methods are often alternate constructors. The usual constructor accepts
individual Python values. The alternate constructor accepts saved dictionary
data:

```python
hero = Combatant.from_dict(saved_data)
```

Using `cls(...)` instead of spelling `Combatant(...)` also allows a future
subclass to receive an instance of that subclass.

### `@property`

`@property` lets a method be read like an attribute:

```python
@property
def is_conscious(self) -> bool:
    return self.hit_points > 0 and "unconscious" not in self.conditions
```

The caller writes `hero.is_conscious` instead of `hero.is_conscious()`. A
property works well when the answer is calculated from current attributes and
reading it does not perform a surprising action.

The project does not currently need `@staticmethod`. A static method belongs in
a class namespace but receives neither `self` nor `cls`. A regular module-level
function is usually clearer when no object or class is required.

Learn more:

- W3Schools: [Python decorators](https://www.w3schools.com/python/python_decorators.asp)
- W3Schools: [Python dataclasses](https://www.w3schools.com/python/ref_module_dataclasses.asp)
- Python docs: [`dataclasses`](https://docs.python.org/3/library/dataclasses.html)
- Python docs: [`classmethod` and `property`](https://docs.python.org/3/library/functions.html)

## 2. Classes, objects, attributes, and methods

A class is a blueprint. An object is one value created from that blueprint:

```python
goblin_one = create_monster("goblin")
goblin_two = create_monster("goblin")
```

Both objects follow the `Combatant` blueprint, but each has its own hit points.
Damaging `goblin_one` does not damage `goblin_two`.

### Instance attributes

Instance attributes belong to one object. Dataclass field declarations describe
which instance attributes will exist:

```python
@dataclass
class Combatant:
    name: str
    armor_class: int
    hit_points: int
```

Dot notation reads or changes an attribute:

```python
print(goblin_one.hit_points)
goblin_one.hit_points = 3
```

### Class attributes and module constants

A class attribute is written inside the class but outside its methods. It is
shared through the class unless an instance replaces it:

```python
class ExampleHero:
    game_name = "D&D"  # Shared class attribute.

    def __init__(self, name: str) -> None:
        self.name = name  # Separate instance attribute.
```

This project mostly uses instance attributes. Shared definitions such as
`WEAPONS`, `PLAYER_CLASSES`, and `MONSTERS` are module-level constants instead.
Uppercase names tell readers that the program treats these values as shared
configuration.

### Instance methods

A method is a function defined inside a class. Its first parameter is usually
`self`, which refers to the object receiving the call:

```python
def heal(self, amount: int) -> int:
    previous = self.hit_points
    self.hit_points = min(self.max_hit_points, self.hit_points + amount)
    return self.hit_points - previous
```

Calling `hero.heal(5)` makes `self` refer to `hero` and `amount` equal `5`.

### Composition

Composition means that one object contains another. A `Combatant` contains a
`Weapon` in its `wielded_weapon` attribute. This keeps weapon rules in the
weapon object instead of copying damage information onto every character.

Learn more:

- W3Schools: [Classes and objects](https://www.w3schools.com/python/python_classes.asp)
- W3Schools: [Class properties](https://www.w3schools.com/python/python_class_properties.asp)
- W3Schools: [Class methods](https://www.w3schools.com/python/python_class_methods.asp)
- Python docs: [Classes](https://docs.python.org/3/tutorial/classes.html)

## 3. Parameters, defaults, and the `->` return annotation

In this function header, `attacker` and `target` are required parameters.
`weapon` is optional because it has the default value `None`:

```python
def attack(
    attacker: Combatant,
    target: Combatant,
    weapon: Weapon | None = None,
) -> AttackResult:
    ...
```

When no weapon argument is supplied, the function uses the equipped weapon.
`None` works as a marker meaning "the caller did not provide a value."

### Keyword-only parameters

The single `*` in a signature makes every later argument keyword-only:

```python
def attack(attacker, target, weapon=None, *, advantage=False):
    ...
```

The caller must write `advantage=True`. That is easier to understand than a
bare `True` whose meaning is unclear.

### Avoid mutable default parameters

Default parameter expressions are evaluated once when Python defines the
function. This is dangerous:

```python
def add_condition(condition, conditions=[]):  # Do not copy this pattern.
    conditions.append(condition)
    return conditions
```

Every call that omits `conditions` reuses the same list. Use `None` and create a
new list inside the function instead. Dataclasses solve the same problem with
`field(default_factory=list)` or `field(default_factory=set)`.

### `->` does not provide a default return value

The arrow is a return type hint:

```python
def ability_modifier(score: int) -> int:
    return (score - 10) // 2
```

`-> int` tells people and development tools that the function intends to return
an integer. It does not create or enforce a return value. The `return` statement
produces the real result.

A function with no `return` statement automatically returns `None`:

```python
def show_name(name: str) -> None:
    print(name)

result = show_name("Liam")
print(result)  # None
```

Common return annotations in this project include:

| Annotation | Meaning |
| --- | --- |
| `-> int` | Returns an integer. |
| `-> None` | Performs work without returning a useful value. |
| `-> Combatant` | Returns one `Combatant` object. |
| `-> Combatant \| None` | Returns a combatant or `None`. |
| `-> list[Combatant]` | Returns a list containing combatants. |
| `-> tuple[bool, int, int]` | Returns three values in a fixed order. |

Type hints are guidance. Python does not normally reject a wrong type at run
time, so tests and validation are still necessary.

Learn more:

- W3Schools: [Function arguments](https://www.w3schools.com/python/python_arguments.asp)
- W3Schools: [Python type hints](https://www.w3schools.com/python/python_type_hints.asp)
- Python docs: [Default argument values](https://docs.python.org/3/tutorial/controlflow.html#default-argument-values)
- Python docs: [`typing`](https://docs.python.org/3/library/typing.html)

## 4. Double-underscore methods and names

Names surrounded by two underscores are often called "dunder" names, short for
"double underscore." Python gives these names special meaning. Do not invent a
new dunder name; use only names Python documents.

### `__init__()` and `__post_init__()`

Python calls `__init__()` after creating a new object. `Encounter` writes this
method explicitly because it has setup logic. Dataclass classes such as
`Weapon` receive a generated `__init__()` instead.

A dataclass calls `__post_init__()` immediately after its generated
`__init__()`. `Combatant.__post_init__()` validates values and calculates
`max_hit_points` after all fields have been assigned.

### `__str__()`

`str(object)` and `print(object)` use `object.__str__()` when it exists.
`AttackResult.__str__()` turns an attack result into a sentence for the DM.

### `__name__`

Every module has a `__name__`. When Python runs `main.py` directly, its name is
`"__main__"`. When another file imports it, its name is `"main"`:

```python
if __name__ == "__main__":
    main()
```

This guard starts the program only when the file is run directly. Importing the
functions for a test does not launch the interactive prompt.

### `__file__` and `__all__`

`__file__` stores the current module's path. The loaders use it to find data
folders relative to the source code instead of depending on the terminal's
current directory.

`main.__all__` lists the names intended as the module's public interface. It is
documentation for readers and affects `from main import *`.

Learn more:

- W3Schools: [`__init__()`](https://www.w3schools.com/python/python_class_init.asp)
- W3Schools: [Class methods and `__str__()`](https://www.w3schools.com/python/python_class_methods.asp)
- Python docs: [Special method names](https://docs.python.org/3/reference/datamodel.html#special-method-names)
- Python docs: [`__main__`](https://docs.python.org/3/library/__main__.html)

## 5. Regular expressions and dice notation

A regular expression, or regex, describes a text pattern. `combat.py` compiles
this pattern once and reuses it:

```python
_EXPR_PATTERN = re.compile(
    r"^(\d*)d(\d+)(?:\s*([+-])\s*(\d+))?$",
    re.IGNORECASE,
)
```

The leading `r` creates a raw string. Backslashes remain available to the regex
engine instead of being treated as Python string escapes.

Read the pattern from left to right:

| Pattern | Meaning |
| --- | --- |
| `^` | Start of the string. |
| `(\d*)` | Capture zero or more digits for the number of dice. |
| `d` | Match the letter `d`. |
| `(\d+)` | Capture one or more digits for the number of sides. |
| `(?:...)` | Group without saving the whole group. |
| `\s*` | Allow zero or more whitespace characters. |
| `([+-])` | Capture either a plus or minus sign. |
| `?` | Make the modifier group optional. |
| `$` | End of the string. |

The pattern accepts `d20`, `2d6+3`, and `1d8 - 1`. It rejects `two d6` and
`2d6 extra`. `fullmatch()` requires the whole input to fit the pattern.

Learn more:

- W3Schools: [Python regular expressions](https://www.w3schools.com/python/python_regex.asp)
- Python docs: [`re` regular expressions](https://docs.python.org/3/library/re.html)

## 6. Reading, writing, and importing files

### Building paths

The project uses `pathlib.Path` instead of assembling paths with strings:

```python
DATA_DIRECTORY = Path(__file__).parent / "data"
```

`Path(__file__)` represents the current Python file. `.parent` selects its
folder. The `/` operator joins another path component on Windows, macOS, or
Linux.

### Reading text and JSON

`sheet_loader.py` reads a whole text file and converts the JSON text into
Python values:

```python
text = path.read_text(encoding="utf-8")
data = json.loads(text)
```

Other loaders demonstrate a context manager:

```python
with path.open("r", encoding="utf-8") as json_file:
    data = json.load(json_file)
```

`"r"` means read mode. The `with` block closes the file even if JSON parsing
raises an exception. Explicit UTF-8 encoding makes behavior consistent across
computers.

### Writing JSON

`Encounter.save()` creates a parent directory and writes formatted JSON:

```python
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("w", encoding="utf-8") as json_file:
    json.dump(self.to_dict(), json_file, indent=2)
```

`"w"` means write mode and replaces an existing file. `indent=2` makes the JSON
readable to humans. Custom objects are converted into dictionaries because JSON
understands basic types rather than arbitrary Python classes.

### Importing Python modules

These two forms behave differently:

```python
import json
from pathlib import Path
```

With `import json`, the module name remains visible: `json.load(...)`. With
`from pathlib import Path`, the selected name can be used directly: `Path(...)`.

Imports normally belong at the top of a file in three groups: standard library,
third-party packages, and local project imports. Blank lines separate groups.
Local imports inside methods are used rarely, usually to avoid a circular import
where two modules try to import each other before either finishes loading.

Learn more:

- W3Schools: [File handling](https://www.w3schools.com/python/python_file_handling.asp)
- W3Schools: [Modules](https://www.w3schools.com/python/python_modules.asp)
- Python docs: [`pathlib`](https://docs.python.org/3/library/pathlib.html)
- Python docs: [`json`](https://docs.python.org/3/library/json.html)
- Python docs: [The import system](https://docs.python.org/3/reference/import.html)

## 7. Why `from __future__ import annotations` appears first

Most modules begin with:

```python
from __future__ import annotations
```

A future import activates behavior that became standard in a newer Python
version or is being introduced gradually. It must appear near the top of the
file, after the module docstring and before normal imports.

The `annotations` feature postpones evaluation of type hints. Python stores an
annotation for later instead of immediately looking up every referenced class.
That allows a class method to say it returns its own class while that class is
still being defined:

```python
class Weapon:
    @classmethod
    def from_dict(cls, data: dict) -> Weapon:
        ...
```

Without postponed annotations, older Python versions require quotes around the
forward reference: `-> "Weapon"`.

Learn more:

- Python docs: [`__future__`](https://docs.python.org/3/library/__future__.html)
- Python docs: [Annotations best practices](https://docs.python.org/3/howto/annotations.html)

## 8. Writing and using test scripts

Tests are small programs that verify other code. This project uses the standard
library's `unittest` framework, so no testing package needs to be installed.

### How test discovery works

```powershell
python -m unittest -v
```

`-m unittest` runs the `unittest` module as a program. `-v` means verbose, so
each test name and docstring appear in the output. Discovery looks for files
named `test*.py`, classes derived from `unittest.TestCase`, and methods whose
names begin with `test`.

### Arrange, Act, Assert

A clear test usually has three parts:

1. **Arrange** the objects and inputs.
2. **Act** by calling the code being tested.
3. **Assert** that the observed result is correct.

```python
def test_resistance_halves_damage_rounding_down(self):
    # Arrange
    target = fighter(hp=20)
    target.resistances.add("slashing")

    # Act
    result = attack(
        fighter(),
        target,
        WEAPONS["sword"],
        roller=FixedRoller(15, 4),
    )

    # Assert
    self.assertEqual(result.damage_dealt, 3)
    self.assertEqual(target.hit_points, 17)
```

### Why tests replace random dice

A test should produce the same result every time. Real random dice could make a
test pass once and fail later. `FixedRoller` stores prepared values. Both it and
the normal roller satisfy the `Roller` protocol because both provide
`randint()`.

Passing a dependency from outside is called dependency injection. The same
idea makes `setup_combat()` testable: a lambda supplies prepared answers and
`messages.append` captures output without using the real keyboard or screen.

### Common assertions

| Assertion | Use it to check |
| --- | --- |
| `assertEqual(actual, expected)` | Two values are equal. |
| `assertTrue(value)` | A condition is true. |
| `assertFalse(value)` | A condition is false. |
| `assertIs(value, object)` | Two names refer to the same object. |
| `assertIsNone(value)` | A value is exactly `None`. |
| `assertIn(item, collection)` | A collection contains an item. |
| `assertRaises(Error)` | Code raises the expected exception. |

Test validation errors with a context manager:

```python
def test_invalid_ability_score_is_rejected(self):
    with self.assertRaises(ValueError):
        ability_modifier(100)
```

### Test one behavior at a time

A good test has one main reason to fail. It may use several assertions to check
different parts of the same result. Avoid making one test perform an entire
ten-round encounter because a failure would be difficult to locate.

Tests can run in any order. Each test should create fresh combatants rather than
depending on an object changed by an earlier test. The `fighter()` helper makes
that easy.

If a test creates a file, remove it even when an assertion fails. The save/load
test uses `try` and `finally`. Python always runs the `finally` block, so the
temporary file is cleaned up.

### Run all or part of the suite

Run everything:

```powershell
python -m unittest -v
```

Run one file:

```powershell
python -m unittest -v test_main
```

Run one test class:

```powershell
python -m unittest -v test_main.CombatRulesTests
```

Run one method:

```powershell
python -m unittest -v test_main.CombatRulesTests.test_dice_expression_rolling
```

### Read failures and errors differently

- `FAIL` means the test ran, but an assertion found the wrong result.
- `ERROR` means an unexpected exception stopped the test.
- Start at the bottom of the traceback to read the exception message.
- Move upward to find the first line that belongs to this project.

### A complete beginner exercise

Add a test showing that immunity prevents damage:

```python
def test_immunity_prevents_all_damage(self):
    target = fighter(hp=20)
    target.immunities.add("slashing")

    result = attack(
        fighter(),
        target,
        WEAPONS["sword"],
        roller=FixedRoller(15, 8),
    )

    self.assertEqual(result.damage_dealt, 0)
    self.assertEqual(target.hit_points, 20)
```

Then deliberately change `20` to `19`, run the test, and study the failure.
Change it back and confirm the suite is green again.

### A safe feature-development cycle

1. Describe one behavior in a test name.
2. Arrange the smallest example that demonstrates it.
3. Run the test and watch it fail for the expected reason.
4. Write the simplest code that makes it pass.
5. Run the full suite to find unintended side effects.
6. Improve names or remove duplication while tests remain green.
7. Commit the working change.

Learn more:

- Python docs: [`unittest`](https://docs.python.org/3/library/unittest.html)
- Python docs: [`unittest` command line](https://docs.python.org/3/library/unittest.html#command-line-interface)
- W3Schools: [Python exercises](https://www.w3schools.com/python/exercise.asp)

## Suggested next lessons

1. Add the immunity test shown above.
2. Add a weapon to `data/weapons.json` and load it in the console.
3. Create a custom monster JSON file and write a test for it.
4. Add a `critical_range` attribute so some attackers can crit on 19 or 20.
5. Extract one encounter command into its own function and test it directly.

Make one change at a time, give it a descriptive test, and keep the full suite
passing.
