# Learning Python with the D&D Encounter Manager

This project is a working program and a collection of small Python lessons.
You do not need to understand every file before changing it. Start with one
idea, make a small change, run the tests, and observe what happens.

## A good order for reading the project

1. Open `character_sheets/liam.json`. This is data rather than Python code.
2. Open `models.py` and find the `Weapon` and `Combatant` classes.
3. Open `combat.py` and follow the `attack()` function from top to bottom.
4. Open `test_main.py` and read one test that calls `attack()`.
5. Open `sheet_loader.py` to see how JSON becomes a `Combatant` object.
6. Open `dm_setup.py` to see loops, conditions, `input()`, and `print()`.
7. Read `encounter.py` last. It combines all the earlier ideas.

Run the program from the project directory:

```powershell
python main.py
```

Run the tests after each code change:

```powershell
python -m unittest -v
```

## How an attack moves through the code

```text
DM enters an attack command
        |
        v
encounter.py finds the attacker and target
        |
        v
combat.py rolls the d20 and damage dice
        |
        v
models.py changes the target's hit points
        |
        v
AttackResult creates a message for the DM
```

This separation is useful because each file has one main job. A test can call
the combat rules directly without pretending to type commands into the full
program.

After completing this introduction, continue with the
[Python Deep Dive](PYTHON_DEEP_DIVE.md). It explains decorators, class
attributes and methods, default parameters, return annotations, dunder methods,
regular expressions, imports, file operations, future imports, and test design
using examples from this project.

## Python ideas used in this project

### Variables and built-in data types

The project uses strings for names, integers for hit points, lists for ordered
combatants, sets for unique conditions, tuples for fixed collections, and
dictionaries for values found by key.

- W3Schools: [Python data types](https://www.w3schools.com/python/python_datatypes.asp)
- W3Schools: [Python dictionaries](https://www.w3schools.com/python/python_dictionaries.asp)
- Python docs: [Data structures](https://docs.python.org/3/tutorial/datastructures.html)

Try this: print `liam.ability_scores["strength"]`, then add a new dictionary
entry and print the dictionary again.

### Functions and return values

A function gives a name to a reusable operation. For example,
`ability_modifier(16)` returns `3`. Parameters are the information a function
receives, and `return` sends a result back to the caller.

- W3Schools: [Python functions](https://www.w3schools.com/python/python_functions.asp)
- Python docs: [Defining functions](https://docs.python.org/3/tutorial/controlflow.html#defining-functions)

Try this: call `roll_expression("2d6+3")` five times and compare the results.

### Modules and imports

Each `.py` file is a module. An import lets one module reuse names from
another. `main.py` imports the project's public tools and acts as its entry
point.

- W3Schools: [Python modules](https://www.w3schools.com/python/python_modules.asp)
- Python docs: [Modules](https://docs.python.org/3/tutorial/modules.html)

Try this: create a temporary `practice.py` file, import `create_monster` from
`main`, and print a Goblin.

### Classes, objects, and dataclasses

A class describes a kind of object. An object is one instance of that class.
`Combatant` is a class; Liam and Goblin are separate `Combatant` objects.
`@dataclass` asks Python to create repetitive methods such as `__init__()`.

- W3Schools: [Python classes and objects](https://www.w3schools.com/python/python_classes.asp)
- Python docs: [Classes](https://docs.python.org/3/tutorial/classes.html)
- Python docs: [`dataclasses`](https://docs.python.org/3/library/dataclasses.html)

Try this: create two Goblins and damage only one. Print both HP values to prove
that each object keeps its own state.

### Type hints and protocols

Annotations such as `name: str` and `-> Combatant` explain what kind of value
is expected. Python does not normally enforce these hints while the program
runs, but editors use them to catch mistakes and provide better suggestions.
The `Roller` protocol describes any object with a compatible `randint()`
method, which is why tests can replace random dice with `FixedRoller`.

- Python docs: [`typing`](https://docs.python.org/3/library/typing.html)
- W3Schools: [Python type hints](https://www.w3schools.com/python/python_type_hints.asp)

Try this: hover over `attack` in PyCharm and inspect the parameter types.

### Conditions, loops, and comprehensions

`if`, `elif`, and `else` choose which code runs. `for` and `while` repeat code.
Comprehensions build collections, as in `{name.lower() for name in names}`.

- W3Schools: [Python conditions](https://www.w3schools.com/python/python_conditions.asp)
- W3Schools: [Python loops](https://www.w3schools.com/python/python_for_loops.asp)
- Python docs: [Control flow](https://docs.python.org/3/tutorial/controlflow.html)

Try this: add a condition to a combatant and use a loop to print every current
condition in uppercase.

### Exceptions and validation

Invalid user input or malformed JSON can cause an exception. `try` and
`except` let the program respond with a helpful message. `raise ValueError(...)`
rejects data that does not meet the program's rules.

- W3Schools: [Python try/except](https://www.w3schools.com/python/python_try_except.asp)
- Python docs: [Errors and exceptions](https://docs.python.org/3/tutorial/errors.html)

Try this: call `ability_modifier(100)` and read the traceback from bottom to
top. Then catch that `ValueError` in a small practice script.

### Files, paths, context managers, and JSON

`Path` represents a filesystem path. A `with` block closes a file even if an
error occurs. The `json` module converts JSON text into Python dictionaries and
converts dictionaries back into JSON.

- W3Schools: [File handling](https://www.w3schools.com/python/python_file_handling.asp)
- W3Schools: [Python JSON](https://www.w3schools.com/python/python_json.asp)
- Python docs: [`pathlib`](https://docs.python.org/3/library/pathlib.html)
- Python docs: [`json`](https://docs.python.org/3/library/json.html)

Try this: copy `liam.json`, change the character's name and class, and load the
new sheet from the DM setup prompt.

### Regular expressions

`combat.py` uses regular expressions to recognize dice text such as `d20` and
`2d6+3`. A regular expression is a compact pattern for matching strings.

- W3Schools: [Python regular expressions](https://www.w3schools.com/python/python_regex.asp)
- Python docs: [`re`](https://docs.python.org/3/library/re.html)

Try this: predict whether `2d8-1`, `d6`, and `two d6` match before running them.

### Input, output, and f-strings

`input()` reads text from the user. `print()` displays text. An f-string, such
as `f"HP: {hit_points}"`, inserts a value into a string.

- W3Schools: [`input()`](https://www.w3schools.com/python/ref_func_input.asp)
- W3Schools: [f-strings](https://www.w3schools.com/python/python_strings_format.asp)
- Python docs: [Input and output](https://docs.python.org/3/tutorial/inputoutput.html)

### Automated tests

Each method in `CombatRulesTests` sets up an example, runs the code, and checks
the result. Predictable dice make the tests repeatable.

- Python docs: [`unittest`](https://docs.python.org/3/library/unittest.html)
- W3Schools: [Python exercises](https://www.w3schools.com/python/exercise.asp)

Try this: write a test proving that an immune target takes zero damage.

## Style and documentation

The code follows PEP 8 for naming, imports, indentation, whitespace, and line
wrapping. Public modules, classes, and functions use docstrings following PEP
257. Comments explain decisions or unfamiliar rules instead of repeating the
code word for word. A line may occasionally be wrapped where it is easiest for
a new programmer to read, because readability is the purpose of the style
guide.

- [PEP 8: Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257: Docstring Conventions](https://peps.python.org/pep-0257/)

When adding code, use four spaces for each indentation level, choose descriptive
names, write a short docstring for each public function, and run the tests.
