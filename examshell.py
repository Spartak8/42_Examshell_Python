#!/usr/bin/env python3

import os
import sys
import ast
import copy
import pickle
import time
import shutil
import random
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Configure UTF-8 encoding for standard I/O (essential for cross-platform Unicode support on Windows)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Enable ANSI colors on Windows terminals
if os.name == "nt":
    os.system("")

# ══════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════

EXAM_DURATION_HOURS = 3
FUNCTION_TIMEOUT_SECONDS = 10
BASE_DIR = Path(__file__).parent.resolve()
RENDU_DIR = BASE_DIR / "rendu"
SUBJECT_DIR = BASE_DIR / "subject"
TRACES_DIR = BASE_DIR / "traces"
WORKER_PATH = BASE_DIR / "exam_worker.py"


# ══════════════════════════════════════════════════════════════
# ANSI Color Helpers
# ══════════════════════════════════════════════════════════════

class C:
    """ANSI escape codes for colored terminal output."""
    RST  = "\033[0m"
    B    = "\033[1m"
    DIM  = "\033[2m"
    R    = "\033[91m"
    G    = "\033[92m"
    Y    = "\033[93m"
    BL   = "\033[94m"
    M    = "\033[95m"
    CY   = "\033[96m"
    W    = "\033[97m"
    BG_R = "\033[41m"
    BG_G = "\033[42m"


def clear():
    """Clear terminal screen (cross-platform)."""
    os.system("cls" if os.name == "nt" else "clear")


def input_until(prompt, deadline=None):
    """Read a line, raising TimeoutError if an absolute deadline is reached."""
    if deadline is None:
        return input(prompt)

    remaining = (deadline - datetime.now()).total_seconds()
    if remaining <= 0:
        raise TimeoutError

    if os.name == "nt" and sys.stdin.isatty():
        import msvcrt

        print(prompt, end="", flush=True)
        characters = []
        while datetime.now() < deadline:
            if not msvcrt.kbhit():
                time.sleep(0.05)
                continue
            char = msvcrt.getwch()
            if char in ("\r", "\n"):
                print()
                return "".join(characters)
            if char == "\x03":
                raise KeyboardInterrupt
            if char == "\x1a":
                raise EOFError
            if char in ("\b", "\x7f"):
                if characters:
                    characters.pop()
                    print("\b \b", end="", flush=True)
                continue
            if char in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue
            characters.append(char)
            print(char, end="", flush=True)
        print()
        raise TimeoutError

    if os.name != "nt" and sys.stdin.isatty():
        import select

        print(prompt, end="", flush=True)
        ready, _, _ = select.select([sys.stdin], [], [], remaining)
        if not ready:
            print()
            raise TimeoutError
        line = sys.stdin.readline()
        if line == "":
            raise EOFError
        return line.rstrip("\n")

    value = input(prompt)
    if datetime.now() >= deadline:
        raise TimeoutError
    return value


# ══════════════════════════════════════════════════════════════
# Exams Registry
# ══════════════════════════════════════════════════════════════

EXAMS = {
    "exam03": {
        "id": "exam03",
        "name": "Exam 03",
        "title": "Exam 03 — Core Python Algorithms",
        "level_points": {1: 16, 2: 16, 3: 17, 4: 17, 5: 17, 6: 17},
        "levels": {
            1: [
                {"name": "py_bracket_validator", "func": "bracket_validator"},
                {"name": "py_cryptic_sorter",     "func": "cryptic_sorter"},
            ],
            2: [
                {"name": "py_echo_validator",    "func": "echo_validator"},
                {"name": "py_mirror_matrix",      "func": "mirror_matrix"},
            ],
            3: [
                {"name": "py_hidenp",                   "func": "hidenp"},
                {"name": "py_inter",                    "func": "inter"},
                {"name": "py_number_base_converter",    "func": "number_base_converter"},
                {"name": "py_pattern_tracker",          "func": "pattern_tracker"},
            ],
            4: [
                {"name": "py_anagram",                    "func": "anagram"},
                {"name": "py_shadow_merge",               "func": "shadow_merge"},
                {"name": "py_string_permutation_checker", "func": "string_permutation_checker"},
            ],
            5: [
                {"name": "py_string_sculptor", "func": "string_sculptor"},
                {"name": "py_twist_sequence",  "func": "twist_sequence"},
            ],
            6: [
                {"name": "py_whisper_cipher",  "func": "whisper_cipher"},
            ],
        }
    },
    "exam04": {
        "id": "exam04",
        "name": "Exam 04",
        "title": "Exam 04 — Advanced Python Algorithms",
        "level_points": {1: 25, 2: 25, 3: 25, 4: 25},
        "levels": {
            1: [
                {"name": "py_array_rotation_detector", "func": "array_rotation_detector"},
                {"name": "py_constellation_mapper",     "func": "constellation_mapper"},
            ],
            2: [
                {"name": "py_list_intersection_finder", "func": "list_intersection_finder"},
                {"name": "py_merge_sorted_lists",        "func": "merge_sorted_lists"},
            ],
            3: [
                {"name": "py_package_dependency_resolver", "func": "package_dependency_resolver"},
                {"name": "py_palindrome_partitioner",      "func": "palindrome_partitioner"},
            ],
            4: [
                {"name": "py_sliding_window_maximum",      "func": "sliding_window_maximum"},
            ],
        }
    }
}


# ══════════════════════════════════════════════════════════════
# Starter Code Templates
# ══════════════════════════════════════════════════════════════

SIGNATURES = {
    # ── Exam 03 ───────────────────────────────────────────────
    "py_bracket_validator":
        "def bracket_validator(s: str) -> bool:\n    # Write your solution here\n    pass\n",
    "py_cryptic_sorter":
        "def cryptic_sorter(strings: list[str]) -> list[str]:\n    # Write your solution here\n    pass\n",
    "py_echo_validator":
        "def echo_validator(text: str) -> bool:\n    # Write your solution here\n    pass\n",
    "py_mirror_matrix":
        "def mirror_matrix(matrix: list[list[int]]) -> list[list[int]]:\n    # Write your solution here\n    pass\n",
    "py_hidenp":
        "def hidenp(small: str, big: str) -> bool:\n    # Write your solution here\n    pass\n",
    "py_inter":
        "def inter(s1: str, s2: str) -> str:\n    # Write your solution here\n    pass\n",
    "py_number_base_converter":
        "def number_base_converter(number: str, from_base: int, to_base: int) -> str:\n    # Write your solution here\n    pass\n",
    "py_pattern_tracker":
        "def pattern_tracker(text: str) -> int:\n    # Write your solution here\n    pass\n",
    "py_anagram":
        "def anagram(s1: str, s2: str) -> bool:\n    # Write your solution here\n    pass\n",
    "py_shadow_merge":
        "def shadow_merge(list1: list[int], list2: list[int]) -> list[int]:\n    # Write your solution here\n    pass\n",
    "py_string_permutation_checker":
        "def string_permutation_checker(s1: str, s2: str) -> bool:\n    # Write your solution here\n    pass\n",
    "py_string_sculptor":
        "def string_sculptor(text: str) -> str:\n    # Write your solution here\n    pass\n",
    "py_twist_sequence":
        "def twist_sequence(arr: list[int], k: int) -> list[int]:\n    # Write your solution here\n    pass\n",
    "py_whisper_cipher":
        "def whisper_cipher(text: str, shift: int) -> str:\n    # Write your solution here\n    pass\n",

    # ── Exam 04 ───────────────────────────────────────────────
    "py_array_rotation_detector":
        "def array_rotation_detector(arr1: list[int], arr2: list[int]) -> bool:\n    # Write your solution here\n    pass\n",
    "py_constellation_mapper":
        "def constellation_mapper(stars: list[tuple[int, int]], size: int) -> list[str]:\n    # Write your solution here\n    pass\n",
    "py_list_intersection_finder":
        "def list_intersection_finder(lists: list[list[int]]) -> list[int]:\n    # Write your solution here\n    pass\n",
    "py_merge_sorted_lists":
        "def merge_sorted_lists(lists: list[list[int]]) -> list[int]:\n    # Write your solution here\n    pass\n",
    "py_package_dependency_resolver":
        "def package_dependency_resolver(packages: dict[str, list[str]]) -> list[str]:\n    # Write your solution here\n    pass\n",
    "py_palindrome_partitioner":
        "def palindrome_partitioner(s: str) -> int:\n    # Write your solution here\n    pass\n",
    "py_sliding_window_maximum":
        "def sliding_window_maximum(nums: list[int], k: int) -> list[int]:\n    # Write your solution here\n    pass\n",
}


# ══════════════════════════════════════════════════════════════
# Embedded Subjects
# ══════════════════════════════════════════════════════════════

SUBJECTS = {
    # ── Exam 03 ───────────────────────────────────────────────
    "py_bracket_validator": """## Subject

```BASH
Assignment name  : py_bracket_validator
Expected files   : py_bracket_validator.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that checks if the brackets in a string are valid.
A string is valid if every opening bracket has a matching closing bracket
in the correct order.
Allowed brackets: (), [], {}

Function signature:
def bracket_validator(s: str) -> bool:

Examples:

Input:
bracket_validator("()")
Output:
True

Input:
bracket_validator("()[]{}")
Output:
True

Input:
bracket_validator("(]")
Output:
False

Input:
bracket_validator("([)]")
Output:
False

Input:
bracket_validator("{[]}")
Output:
True

Input:
bracket_validator("hello(world)")
Output:
True

Input:
bracket_validator("((())")
Output:
False

Input:
bracket_validator("")
Output:
True
```
""",

    "py_cryptic_sorter": """## Subject

```BASH
Assignment name  : py_cryptic_sorter
Expected files   : py_cryptic_sorter.py
Forbidden functions: sorted(), .sort()
--------------------------------------------------------------------------------

Write a function that sorts a list of strings according to multiple criteria:
1. Primary sort: By string length (shortest first)
2. Secondary sort: ASCII order, except letters are compared case-insensitively
   (for strings of same length)
3. Strings that compare equally must remain in their original input order
   (the manual sort must be stable).

IMPORTANT:
- You must implement the sorting logic manually.
- The built-in sorted() function is forbidden.
- The list.sort() method (or any .sort() call) is forbidden.
- Using a forbidden function causes grademe to reject the submission.

Function signature:
def cryptic_sorter(strings: list[str]) -> list[str]:

Examples:

Input:
cryptic_sorter(["apple", "cat", "banana", "dog", "elephant"])
Output:
["cat", "dog", "apple", "banana", "elephant"]

Input:
cryptic_sorter(["hello", "world", "hi", "test"])
Output:
["hi", "test", "hello", "world"]

Input:
cryptic_sorter([])
Output:
[]

Input:
cryptic_sorter([""])
Output:
[""]
```
""",

    "py_echo_validator": """## Subject

```BASH
Assignment name  : py_echo_validator
Expected files   : py_echo_validator.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that checks if a string is a palindrome,
ignoring spaces and case, only consider alphabetic characters
for the comparison.
Note: an empty string is NOT considered a palindrome (returns False).
If the input contains no alphabetic characters, return False.

Function signature:
def echo_validator(text: str) -> bool:

Examples:

Input:
echo_validator("racecar")
Output:
True

Input:
echo_validator("A man a plan a canal Panama")
Output:
True

Input:
echo_validator("race a car")
Output:
False

Input:
echo_validator("Was it a car or a cat I saw")
Output:
True

Input:
echo_validator("hello")
Output:
False

Input:
echo_validator("Madam Im Adam")
Output:
True

Input:
echo_validator("")
Output:
False
```
""",

    "py_mirror_matrix": """## Subject

```BASH
Assignment name  : py_mirror_matrix
Expected files   : py_mirror_matrix.py
Allowed functions: 
--------------------------------------------------------------------------------

Given a 2D matrix (list of lists), return a new matrix where each row
is reversed.

Function signature:
def mirror_matrix(matrix: list[list[int]]) -> list[list[int]]:

Examples:

Input:
mirror_matrix([[1,2,3],[4,5,6]])
Output:
[[3,2,1],[6,5,4]]

Input:
mirror_matrix([[1,2],[3,4],[5,6]])
Output:
[[2,1],[4,3],[6,5]]

Input:
mirror_matrix([[7]])
Output:
[[7]]

Input:
mirror_matrix([[1,2,3,4]])
Output:
[[4,3,2,1]]

Input:
mirror_matrix([[-1,-2],[-3,-4]])
Output:
[[-2,-1],[-4,-3]]
```
""",

    "py_hidenp": """## Subject

```BASH
Assignment name  : py_hidenp
Expected files   : py_hidenp.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that checks if the string 'small' is a subsequence
of 'big'. A subsequence means all characters of 'small' appear in 'big'
in the same order, but not necessarily consecutively.
Function is case-sensitive.

Function signature:
def hidenp(small: str, big: str) -> bool:

Examples:

Input:
hidenp("abc", "a1b2c3")
Output:
True

Input:
hidenp("ace", "abcde")
Output:
True

Input:
hidenp("aec", "abcde")
Output:
False

Input:
hidenp("", "abc")
Output:
True

Input:
hidenp("abc", "ab")
Output:
False

Input:
hidenp("aaaa", "aaa")
Output:
False

Input:
hidenp("sing","subsequence testing")
Output:
True
```
""",

    "py_inter": """## Subject

```BASH
Assignment name  : py_inter
Expected files   : py_inter.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that returns a string with the characters that appear
in both strings, without repetitions. Characters are added in the order
they appear in the first string.

Function signature:
def inter(s1: str, s2: str) -> str:

Examples:

Input:
inter("hello", "world")
Output:
"lo"

Input:
inter("banana", "band")
Output:
"ban"

Input:
inter("abcabc", "bc")
Output:
"bc"

Input:
inter("abc", "xyz")
Output:
""

Input:
inter("", "abc")
Output:
""
```
""",

    "py_number_base_converter": """## Subject

```BASH
Assignment name  : py_number_base_converter
Expected files   : py_number_base_converter.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that converts a number from one base to another.
Support bases from 2 to 36 inclusive.
Use digits 0-9 and letters A-Z for values 10-35.
Return "ERROR" for invalid inputs.
Input letters are case-insensitive, but output letters must be uppercase.
An empty number, sign, whitespace, or digit invalid for from_base is invalid.
Leading zeroes are accepted and should be normalized in the result.

Function signature:
def number_base_converter(number: str, from_base: int, to_base: int) -> str:

Examples:

Input:
number_base_converter("1010", 2, 10)
Output:
"10"

Input:
number_base_converter("FF", 16, 10)
Output:
"255"

Input:
number_base_converter("255", 10, 16)
Output:
"FF"

Input:
number_base_converter("123", 10, 2)
Output:
"1111011"

Input:
number_base_converter("Z", 36, 10)
Output:
"35"

Input:
number_base_converter("35", 10, 36)
Output:
"Z"

Input:
number_base_converter("123", 1, 10)
Output:
"ERROR"

Input:
number_base_converter("G", 16, 10)
Output:
"ERROR"
```
""",

    "py_pattern_tracker": """## Subject

```BASH
Assignment name  : py_pattern_tracker
Expected files   : py_pattern_tracker.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that counts the number of valid consecutive digit pairs
in a string. A valid pair consists of two adjacent digits where the second
digit is exactly one greater than the first.
A 9 followed by a 0 is NOT a valid pair.

Function signature:
def pattern_tracker(text: str) -> int:

Examples:

Input:
pattern_tracker("123")
Output:
2

Input:
pattern_tracker("12a34")
Output:
2

Input:
pattern_tracker("987654321")
Output:
0

Input:
pattern_tracker("01234567")
Output:
7

Input:
pattern_tracker("abc")
Output:
0

Input:
pattern_tracker("1a2b3c4")
Output:
0

Input:
pattern_tracker("112233")
Output:
2
```
""",

    "py_anagram": """## Subject

```BASH
Assignment name  : py_anagram
Expected files   : py_anagram.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that checks if two strings are anagrams.
They must contain exactly the same letters with the same quantity,
ignoring case and spaces.

Function signature:
def anagram(s1: str, s2: str) -> bool:

Examples:

Input:
anagram("listen", "silent")
Output:
True

Input:
anagram("Triangle", "Integral")
Output:
True

Input:
anagram("Dormitory", "Dirty Room")
Output:
True

Input:
anagram("hello", "world")
Output:
False

Input:
anagram("", "")
Output:
True

Input:
anagram("abc", "abcc")
Output:
False
```
""",

    "py_shadow_merge": """## Subject

```BASH
Assignment name  : py_shadow_merge
Expected files   : py_shadow_merge.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that merges two sorted lists into one sorted list.

Function signature:
def shadow_merge(list1: list[int], list2: list[int]) -> list[int]:

Examples:

Input:
shadow_merge([1,3,5], [2,4,6])
Output:
[1,2,3,4,5,6]

Input:
shadow_merge([1,2,3], [4,5,6])
Output:
[1,2,3,4,5,6]

Input:
shadow_merge([1], [2,3,4])
Output:
[1,2,3,4]

Input:
shadow_merge([], [1,2,3])
Output:
[1,2,3]

Input:
shadow_merge([1,1,2], [1,3,3])
Output:
[1,1,1,2,3,3]
```
""",

    "py_string_permutation_checker": """## Subject

```BASH
Assignment name  : py_string_permutation_checker
Expected files   : py_string_permutation_checker.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that determines if two strings are permutations of each other.
Case sensitive. Whitespace and punctuation count as regular characters.
Empty strings are permutations of each other.

Function signature:
def string_permutation_checker(s1: str, s2: str) -> bool:

Examples:

Input:
string_permutation_checker("abc", "bca")
Output:
True

Input:
string_permutation_checker("abc", "def")
Output:
False

Input:
string_permutation_checker("listen", "silent")
Output:
True

Input:
string_permutation_checker("hello", "bello")
Output:
False

Input:
string_permutation_checker("", "")
Output:
True

Input:
string_permutation_checker("a", "")
Output:
False

Input:
string_permutation_checker("Abc", "abc")
Output:
False

Input:
string_permutation_checker("a gentleman","elegant man")
Output:
True
```
""",

    "py_string_sculptor": """## Subject

```BASH
Assignment name  : py_string_sculptor
Expected files   : py_string_sculptor.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that transforms a string by alternating the case of
alphabetic characters only.
Non-alphabetic characters remain unchanged and are NOT counted in the
alternation index.
The first alphabetic character should be lowercase, the second uppercase, etc.
Spaces reset the alternation (next alpha after a space is lowercase again).

Function signature:
def string_sculptor(text: str) -> str:

Examples:

Input:
string_sculptor("hello")
Output:
"hElLo"

Input:
string_sculptor("Hello World")
Output:
"hElLo wOrLd"

Input:
string_sculptor("abc123def")
Output:
"aBc123DeF"

Input:
string_sculptor("Python3.9!")
Output:
"pYtHoN3.9!"

Input:
string_sculptor("")
Output:
""
```
""",

    "py_twist_sequence": """## Subject

```BASH
Assignment name  : py_twist_sequence
Expected files   : py_twist_sequence.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that rotates a list to the right by k positions.
Rotating right by k means the last k elements move to the front.
A negative k rotates left (for example, k=-1 moves the first item to the end).

Function signature:
def twist_sequence(arr: list[int], k: int) -> list[int]:

Examples:

Input:
twist_sequence([1,2,3,4,5], 2)
Output:
[4,5,1,2,3]

Input:
twist_sequence([1,2,3], 1)
Output:
[3,1,2]

Input:
twist_sequence([1,2,3,4], 0)
Output:
[1,2,3,4]

Input:
twist_sequence([1,2,3], 5)
Output:
[2,3,1]

Input:
twist_sequence([], 3)
Output:
[]
```
""",

    "py_whisper_cipher": """## Subject

```BASH
Assignment name  : py_whisper_cipher
Expected files   : py_whisper_cipher.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that creates a Caesar cipher by shifting letters in a
string by a given amount.
Non-alphabetic characters should remain unchanged.
The shift can be negative (shift left).

Function signature:
def whisper_cipher(text: str, shift: int) -> str:

Examples:

Input:
whisper_cipher("hello", 3)
Output:
"khoor"

Input:
whisper_cipher("Hello World!", 1)
Output:
"Ifmmp Xpsme!"

Input:
whisper_cipher("xyz", 3)
Output:
"abc"

Input:
whisper_cipher("ABC123def", 5)
Output:
"FGH123ijk"

Input:
whisper_cipher("", 10)
Output:
""

Input:
whisper_cipher("abc", -3)
Output:
"xyz"
```
""",

    # ── Exam 04 ───────────────────────────────────────────────
    "py_array_rotation_detector": """## Subject

```BASH
Assignment name  : py_array_rotation_detector
Expected files   : py_array_rotation_detector.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that determines if one array is a rotation
of another array.
A rotation means the array has been shifted circularly left
or right.

Function signature:
def array_rotation_detector(arr1: list[int], arr2: list[int]) -> bool:

The function should:
- Check if arr2 is a rotation of arr1
- Handle arrays of different lengths (return False)
- Handle empty arrays (two empty arrays are rotations)
- A rotation can be 0 positions (same array)
- Consider both left and right rotations

Examples:

Input:
array_rotation_detector([1, 2, 3, 4, 5], [3, 4, 5, 1, 2])
Output:
True

Input:
array_rotation_detector([1, 2, 3, 4, 5], [4, 5, 1, 2, 3])
Output:
True

Input:
array_rotation_detector([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
Output:
True

Input:
array_rotation_detector([1, 2, 3, 4, 5], [2, 3, 4, 5, 1])
Output:
True

Input:
array_rotation_detector([1, 2, 3], [1, 3, 2])
Output:
False

Input:
array_rotation_detector([1, 2, 3], [1, 2])
Output:
False

Input:
array_rotation_detector([], [])
Output:
True

Input:
array_rotation_detector([1, 1, 1], [1, 1, 1])
Output:
True
```
""",

    "py_constellation_mapper": """## Subject

```BASH
Assignment name  : py_constellation_mapper
Expected files   : py_constellation_mapper.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that maps a constellation of stars onto a grid
and returns the visual representation as a list of strings.

Function signature:
def constellation_mapper(stars: list[tuple[int, int]], size: int) -> list[str]:

The function should:
- Take a list of star coordinates as tuples (row, col)
  and grid size as integer
- Return a list of strings representing the grid
- Stars are represented by '*' and empty spaces by '.'
- Grid coordinates start from (0, 0) at top-left
- Ignore coordinates outside the grid boundaries
- Handle duplicate coordinates (star appears only once)
- Return an empty list when size is zero or negative

Examples:

Input:
constellation_mapper([(0, 0), (1, 1), (2, 2)], 3)
Output:
['*..', '.*.', '..*']

Input:
constellation_mapper([(1, 1), (0, 1), (2, 1), (1, 0), (1, 2)], 3)
Output:
['.*.', '***', '.*.']

Input:
constellation_mapper([], 2)
Output:
['..', '..']

Input:
constellation_mapper([(0, 0), (0, 0), (1, 1)], 2)
Output:
['*.', '.*']

Input:
constellation_mapper([(0, 0), (5, 5)], 3)
Output:
['*..', '...', '...']

Input:
constellation_mapper([(1, 0), (1, 1), (1, 2)], 3)
Output:
['...', '***', '...']
```
""",

    "py_list_intersection_finder": """## Subject

```BASH
Assignment name  : py_list_intersection_finder
Expected files   : py_list_intersection_finder.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that finds the intersection of
multiple sorted lists.
Return a new list containing elements that appear in
ALL input lists, in sorted order.

Function signature:
def list_intersection_finder(lists: list[list[int]]) -> list[int]:

The function should:
- Return elements that appear in ALL lists
- Result should be sorted in ascending order
- Remove duplicates from the result
- Handle empty input or empty lists gracefully
- If any list is empty, the intersection is empty

Examples:

Input:
list_intersection_finder([[1, 2, 3], [2, 3, 4], [2, 3, 5]])
Output:
[2, 3]

Input:
list_intersection_finder([[1, 2, 3, 4], [2, 4, 6, 8], [4, 8, 12]])
Output:
[4]

Input:
list_intersection_finder([[1, 2, 3], [4, 5, 6]])
Output:
[]

Input:
list_intersection_finder([[1, 1, 2, 3], [1, 2, 2, 3], [1, 2, 3, 3]])
Output:
[1, 2, 3]

Input:
list_intersection_finder([])
Output:
[]

Input:
list_intersection_finder([[1, 2, 3], []])
Output:
[]

Input:
list_intersection_finder([[5]])
Output:
[5]
```
""",

    "py_merge_sorted_lists": """## Subject

```BASH
Assignment name  : py_merge_sorted_lists
Expected files   : py_merge_sorted_lists.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that merges multiple sorted lists
into one sorted list while maintaining the sort order efficiently.

Function signature:
def merge_sorted_lists(lists: list[list[int]]) -> list[int]:

The function should:
- Take a list of sorted integer lists as input
- Return a single merged list in ascending order
- Preserve all duplicate elements in the final result
- Handle empty lists and empty input gracefully
- Maintain optimal efficiency for large inputs

Rules:
- All input lists are guaranteed to be sorted in ascending order
- Empty lists should be ignored during merging
- Return empty list if no valid input is provided
- Preserve duplicates across different lists
- Handle negative numbers correctly

Examples:

Input:
merge_sorted_lists([[1, 3, 5], [2, 4, 6]])
Output:
[1, 2, 3, 4, 5, 6]

Input:
merge_sorted_lists([[1, 5, 9], [2, 3, 8], [4, 6, 7]])
Output:
[1, 2, 3, 4, 5, 6, 7, 8, 9]

Input:
merge_sorted_lists([[5], [1, 3], [2, 4]])
Output:
[1, 2, 3, 4, 5]

Input:
merge_sorted_lists([[1, 1, 2], [2, 3, 3]])
Output:
[1, 1, 2, 2, 3, 3]

Input:
merge_sorted_lists([[], [1, 2, 3]])
Output:
[1, 2, 3]

Input:
merge_sorted_lists([])
Output:
[]

Input:
merge_sorted_lists([[-5, -1, 0], [-3, 2, 4]])
Output:
[-5, -3, -1, 0, 2, 4]

Input:
merge_sorted_lists([[10], [10], [10]])
Output:
[10, 10, 10]
```
""",

    "py_package_dependency_resolver": """## Subject

```BASH
Assignment name  : py_package_dependency_resolver
Expected files   : py_package_dependency_resolver.py
Allowed functions: 
--------------------------------------------------------------------------------

Write a function that determines a valid package installation order
by resolving dependencies.
Use topological sorting to ensure dependencies are installed
before the packages that require them.

Function signature:
def package_dependency_resolver(packages: dict[str, list[str]]) -> list[str]:

The function should:
- Take a dictionary where keys are package names and
  values are lists of dependencies
- Return packages in installation order (dependencies first)
- Return empty list if no valid order exists (circular dependencies)
- Handle empty input and isolated dependency chains
- Ignore references to packages not in the input dictionary

Algorithm requirements:
- Use topological sorting (e.g., Kahn's algorithm)
- Process packages with no remaining dependencies first
- Ensure deterministic output when multiple valid orders exist:
  process all currently available packages as an alphabetically sorted batch,
  then discover the next batch

Examples:

Input:
package_dependency_resolver({
    "app": ["database"],
    "database": ["driver"],
    "driver": []
})
Output:
["driver", "database", "app"]

Input:
package_dependency_resolver({
    "A": [],
    "B": ["A"],
    "C": ["A", "B"]
})
Output:
["A", "B", "C"]

Input:
package_dependency_resolver({})
Output:
[]

Input:
package_dependency_resolver({
    "X": ["Y"],
    "Y": ["X"]
})
Output:
[]

Input:
package_dependency_resolver({
    "web": [],
    "api": [],
    "frontend": ["web"],
    "backend": ["api"]
})
Output:
["api", "web", "backend", "frontend"]
```
""",

    "py_palindrome_partitioner": """## Subject

```BASH
Assignment name  : py_palindrome_partitioner
Expected files   : py_palindrome_partitioner.py
Allowed functions: None
--------------------------------------------------------------------------------

Write a function that finds the minimum number of cuts needed
to partition a string so that every substring is a palindrome.

Function signature:
def palindrome_partitioner(s: str) -> int:

The function should:
- Find minimum cuts to make all parts palindromes
- Return the number of cuts needed (not the number of parts)
- Handle empty strings (return 0)
- Single characters are palindromes
- Case-sensitive palindrome checking

Examples:

Input:
palindrome_partitioner("aab")
Output:
1

Input:
palindrome_partitioner("aba")
Output:
0

Input:
palindrome_partitioner("abcba")
Output:
0

Input:
palindrome_partitioner("abcd")
Output:
3

Input:
palindrome_partitioner("aabaa")
Output:
0

Input:
palindrome_partitioner("abac")
Output:
1

Input:
palindrome_partitioner("")
Output:
0
```
""",

    "py_sliding_window_maximum": """## Subject

```BASH
Assignment name  : py_sliding_window_maximum
Expected files   : py_sliding_window_maximum.py
Allowed functions: None
--------------------------------------------------------------------------------

Write a function that finds the maximum element in
each sliding window of size k in an array.
Return a list of maximums for each window position.

Function signature:
def sliding_window_maximum(nums: list[int], k: int) -> list[int]:

The function should:
- Slide a window of size k through the array
- Find the maximum element in each window position
- Return a list of maximum values
- Handle edge cases (empty array, k <= 0, k > array length)
- Return empty list for invalid inputs

Examples:

Input:
sliding_window_maximum([1, 3, -1, -3, 5, 3, 6, 7], 3)
Output:
[3, 3, 5, 5, 6, 7]

Input:
sliding_window_maximum([1, 2, 3, 4, 5], 2)
Output:
[2, 3, 4, 5]

Input:
sliding_window_maximum([5, 4, 3, 2, 1], 1)
Output:
[5, 4, 3, 2, 1]

Input:
sliding_window_maximum([1, 2, 3], 3)
Output:
[3]

Input:
sliding_window_maximum([1, 2, 3], 4)
Output:
[]

Input:
sliding_window_maximum([], 2)
Output:
[]

Input:
sliding_window_maximum([1, 2, 3], 0)
Output:
[]
```
""",
}


# ══════════════════════════════════════════════════════════════
# Test Cases
# ══════════════════════════════════════════════════════════════

TEST_CASES = {
    # ── Exam 03 / Level 1 ─────────────────────────────────────
    "py_bracket_validator": [
        ("Single pair ()",                  ("()",),                                    True),
        ("Multiple matched pairs ()[]{}",    ("()[]{}",),                                True),
        ("Mismatched pair (]",               ("(]",),                                    False),
        ("Wrong nesting order ([)]",         ("([)]",),                                  False),
        ("Nested brackets {[]}",             ("{[]}",),                                  True),
        ("With surrounding text",            ("hello(world)",),                          True),
        ("Unclosed opening brackets",        ("((())",),                                 False),
        ("Empty string",                     ("",),                                      True),
        ("Single closing bracket",           (")",),                                     False),
        ("Deep nesting",                     ("{[()]}",),                                True),
        ("Mixed text and nested brackets",   ("a{b[c(d)e]f}g",),                         True),
    ],

    "py_cryptic_sorter": [
        ("Varying lengths and words",        (["apple", "cat", "banana", "dog", "elephant"],),
                                             ["cat", "dog", "apple", "banana", "elephant"]),
        ("Mixed lengths with ties",          (["hello", "world", "hi", "test"],),
                                             ["hi", "test", "hello", "world"]),
        ("Empty list",                       ([],),                                      []),
        ("List with empty string",           ([""],),                                    [""]),
        ("Lexical sort on equal lengths",    (["pear", "apple", "fig", "banana"],),
                                             ["fig", "pear", "apple", "banana"]),
        ("Case-insensitive sorting",         (["cat", "BAT", "ant"],),
                                             ["ant", "BAT", "cat"]),
        ("Single character strings",         (["c", "a", "b"],),
                                             ["a", "b", "c"]),
        ("Duplicate values",                 (["dog", "cat", "dog", "ant", "cat"],),
                                             ["ant", "cat", "cat", "dog", "dog"]),
        ("Stable case-insensitive ties",     (["aB", "Ab", "AB", "ab"],),
                                             ["aB", "Ab", "AB", "ab"]),
        ("Empty strings mixed with values",  (["bbb", "", "a", "cc", ""],),
                                             ["", "", "a", "cc", "bbb"]),
        ("Letters, digits, and case",        (["b1", "A2", "a1", "B0"],),
                                             ["a1", "A2", "B0", "b1"]),
        ("Reverse length order",             (["dddd", "ccc", "bb", "a"],),
                                             ["a", "bb", "ccc", "dddd"]),
        ("Numeric strings",                  (["10", "2", "01", "1"],),
                                             ["1", "2", "01", "10"]),
        ("Mixed case words and lengths",     (["Zoo", "apple", "ALPHA", "ant", "zOO"],),
                                             ["ant", "Zoo", "zOO", "ALPHA", "apple"]),
    ],

    # ── Exam 03 / Level 2 ─────────────────────────────────────
    "py_echo_validator": [
        ("Simple palindrome 'racecar'",      ("racecar",),                               True),
        ("Sentence palindrome with spaces",  ("A man a plan a canal Panama",),           True),
        ("Not a palindrome",                 ("race a car",),                            False),
        ("Sentence with mixed case",         ("Was it a car or a cat I saw",),          True),
        ("Common word not palindrome",       ("hello",),                                 False),
        ("Name palindrome",                  ("Madam Im Adam",),                         True),
        ("Empty string is False",            ("",),                                      False),
        ("Single letter",                    ("a",),                                     True),
        ("Complex sentence",                 ("Step on no pets",),                       True),
        ("Punctuation-only is not palindrome",("!? 123",),                              False),
        ("Ignore digits and punctuation",    ("A1, b2, a!",),                            True),
    ],

    "py_mirror_matrix": [
        ("2x3 matrix",                       ([[1, 2, 3], [4, 5, 6]],),                  [[3, 2, 1], [6, 5, 4]]),
        ("3x2 matrix",                       ([[1, 2], [3, 4], [5, 6]],),                [[2, 1], [4, 3], [6, 5]]),
        ("Single element matrix",            ([[7]],),                                   [[7]]),
        ("Single row matrix",                ([[1, 2, 3, 4]],),                          [[4, 3, 2, 1]]),
        ("Negative numbers",                 ([[-1, -2], [-3, -4]],),                    [[-2, -1], [-4, -3]]),
        ("Empty matrix",                     ([],),                                      []),
        ("Matrix with empty sublists",       ([[], []],),                                [[], []]),
    ],

    # ── Exam 03 / Level 3 ─────────────────────────────────────
    "py_hidenp": [
        ("Interleaved subsequence",          ("abc", "a1b2c3"),                          True),
        ("Sparse subsequence",               ("ace", "abcde"),                           True),
        ("Wrong order",                      ("aec", "abcde"),                           False),
        ("Empty small string",               ("", "abc"),                                True),
        ("Small longer than big",            ("abc", "ab"),                              False),
        ("Not enough repeated letters",      ("aaaa", "aaa"),                            False),
        ("Word in phrase",                   ("sing", "subsequence testing"),            True),
        ("Exact match",                      ("hello", "hello"),                         True),
        ("Prefix match",                     ("hello", "hello world"),                   True),
        ("Both empty strings",               ("", ""),                                   True),
    ],

    "py_inter": [
        ("Common letters 'hello' & 'world'", ("hello", "world"),                         "lo"),
        ("Overlapping letters in words",     ("banana", "band"),                         "ban"),
        ("Deduplication in result",          ("abcabc", "bc"),                           "bc"),
        ("Disjoint sets",                    ("abc", "xyz"),                             ""),
        ("Empty first string",               ("", "abc"),                                ""),
        ("Empty second string",              ("abc", ""),                                ""),
        ("Reversed strings",                 ("abcdef", "fedcba"),                       "abcdef"),
        ("Numeric characters",               ("12345", "54321"),                         "12345"),
    ],

    "py_number_base_converter": [
        ("Binary to Decimal",                ("1010", 2, 10),                            "10"),
        ("Hex to Decimal",                   ("FF", 16, 10),                             "255"),
        ("Decimal to Hex",                   ("255", 10, 16),                            "FF"),
        ("Decimal to Binary",                ("123", 10, 2),                             "1111011"),
        ("Base 36 to Decimal",               ("Z", 36, 10),                              "35"),
        ("Decimal to Base 36",               ("35", 10, 36),                             "Z"),
        ("Invalid from_base (< 2)",          ("123", 1, 10),                             "ERROR"),
        ("Invalid character for base",       ("G", 16, 10),                              "ERROR"),
        ("Zero value",                       ("0", 10, 2),                               "0"),
        ("Invalid to_base (> 36)",           ("10", 10, 40),                             "ERROR"),
        ("Lowercase hexadecimal input",      ("ff", 16, 10),                             "255"),
        ("Empty number",                     ("", 10, 2),                                "ERROR"),
        ("Digit invalid for source base",    ("102", 2, 10),                             "ERROR"),
        ("Invalid to_base (< 2)",            ("10", 10, 1),                              "ERROR"),
        ("Leading zeroes normalized",        ("000F", 16, 10),                           "15"),
        ("Signed input is invalid",          ("-10", 10, 2),                             "ERROR"),
    ],

    "py_pattern_tracker": [
        ("Strictly increasing 123",          ("123",),                                   2),
        ("Separated by letter 12a34",        ("12a34",),                                 2),
        ("Decreasing sequence",              ("987654321",),                             0),
        ("Consecutive 0 to 7",               ("01234567",),                              7),
        ("Only letters",                     ("abc",),                                   0),
        ("Alternating letters and numbers",  ("1a2b3c4",),                               0),
        ("Duplicates not consecutive diff",  ("112233",),                                2),
        ("9 followed by 0 is invalid",       ("890",),                                   1),
        ("Empty string",                     ("",),                                      0),
    ],

    # ── Exam 03 / Level 4 ─────────────────────────────────────
    "py_anagram": [
        ("Standard anagram",                 ("listen", "silent"),                       True),
        ("Mixed case anagram",               ("Triangle", "Integral"),                   True),
        ("Anagram with spaces",              ("Dormitory", "Dirty Room"),                True),
        ("Completely different words",       ("hello", "world"),                         False),
        ("Both empty strings",               ("", ""),                                   True),
        ("Different letter counts",          ("abc", "abcc"),                            False),
        ("Another phrase anagram",           ("The eyes", "They see"),                   True),
        ("School master anagram",            ("School master", "The classroom"),         True),
        ("Different lengths",                ("rat", "car"),                             False),
    ],

    "py_shadow_merge": [
        ("Alternating sorted lists",         ([1, 3, 5], [2, 4, 6]),                     [1, 2, 3, 4, 5, 6]),
        ("Non-overlapping ranges",           ([1, 2, 3], [4, 5, 6]),                     [1, 2, 3, 4, 5, 6]),
        ("Single element list",              ([1], [2, 3, 4]),                           [1, 2, 3, 4]),
        ("Empty first list",                 ([], [1, 2, 3]),                            [1, 2, 3]),
        ("Preserving duplicates",            ([1, 1, 2], [1, 3, 3]),                     [1, 1, 1, 2, 3, 3]),
        ("Both empty",                       ([], []),                                   []),
        ("Negative numbers included",        ([-5, 0, 5], [-10, 0, 10]),                 [-10, -5, 0, 0, 5, 10]),
    ],

    "py_string_permutation_checker": [
        ("Simple permutation",               ("abc", "bca"),                             True),
        ("Different characters",             ("abc", "def"),                             False),
        ("Permutation match",                ("listen", "silent"),                       True),
        ("Single character difference",      ("hello", "bello"),                         False),
        ("Both empty strings",               ("", ""),                                   True),
        ("Different lengths",                ("a", ""),                                  False),
        ("Case sensitivity check",           ("Abc", "abc"),                             False),
        ("Sentence permutation",             ("a gentleman", "elegant man"),             True),
        ("Identical strings",                ("same", "same"),                           True),
    ],

    # ── Exam 03 / Level 5 ─────────────────────────────────────
    "py_string_sculptor": [
        ("Single word alternation",          ("hello",),                                 "hElLo"),
        ("Multiple words (space resets)",    ("Hello World",),                           "hElLo wOrLd"),
        ("With digits (digits not counted)", ("abc123def",),                             "aBc123DeF"),
        ("With punctuation",                 ("Python3.9!",),                            "pYtHoN3.9!"),
        ("Empty string",                     ("",),                                      ""),
        ("Single character",                 ("a",),                                     "a"),
        ("Two characters",                   ("ab",),                                    "aB"),
        ("Multiple spaces",                  ("a b c",),                                 "a b c"),
        ("Phrase with various cases",        ("One two THREE",),                         "oNe tWo tHrEe"),
    ],

    "py_twist_sequence": [
        ("Rotate by 2",                      ([1, 2, 3, 4, 5], 2),                       [4, 5, 1, 2, 3]),
        ("Rotate by 1",                      ([1, 2, 3], 1),                             [3, 1, 2]),
        ("Rotate by 0 (identity)",           ([1, 2, 3, 4], 0),                          [1, 2, 3, 4]),
        ("Rotate by length + offset (k=5)",  ([1, 2, 3], 5),                             [2, 3, 1]),
        ("Empty array",                      ([], 3),                                    []),
        ("Single element large k",           ([1], 10),                                  [1]),
        ("Rotate by exact length",           ([10, 20, 30], 3),                          [10, 20, 30]),
        ("Negative shift rotates left",      ([1, 2, 3, 4], -1),                         [2, 3, 4, 1]),
    ],

    # ── Exam 03 / Level 6 ─────────────────────────────────────
    "py_whisper_cipher": [
        ("Shift by 3",                       ("hello", 3),                               "khoor"),
        ("Shift by 1 with punctuation",      ("Hello World!", 1),                        "Ifmmp Xpsme!"),
        ("Wrap around end of alphabet",      ("xyz", 3),                                 "abc"),
        ("Alphanumeric with shift 5",        ("ABC123def", 5),                           "FGH123ijk"),
        ("Empty string",                     ("", 10),                                   ""),
        ("Negative shift (shift left)",      ("abc", -3),                                "xyz"),
        ("Shift 0 (identity)",               ("Python 42", 0),                           "Python 42"),
        ("Shift by 26 (full cycle)",         ("Hello", 26),                              "Hello"),
        ("Single lowercase letter wrap",     ("z", 1),                                   "a"),
        ("Single uppercase letter wrap",     ("Z", 1),                                   "A"),
        ("Large negative shift",             ("Abc-Z", -53),                             "Zab-Y"),
    ],

    # ── Exam 04 / Level 1 ─────────────────────────────────────
    "py_array_rotation_detector": [
        ("Rotation by 2 positions",          ([1, 2, 3, 4, 5], [3, 4, 5, 1, 2]),        True),
        ("Rotation by 3 positions",          ([1, 2, 3, 4, 5], [4, 5, 1, 2, 3]),        True),
        ("Zero rotation (identical)",        ([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]),        True),
        ("Rotation by 1 position",           ([1, 2, 3, 4, 5], [2, 3, 4, 5, 1]),        True),
        ("Not a rotation (wrong order)",     ([1, 2, 3], [1, 3, 2]),                    False),
        ("Different lengths",                ([1, 2, 3], [1, 2]),                       False),
        ("Both empty arrays",                ([], []),                                   True),
        ("All identical elements",           ([1, 1, 1], [1, 1, 1]),                    True),
        ("Single element match",             ([7], [7]),                                 True),
        ("Two elements rotated",             ([1, 2], [2, 1]),                           True),
        ("Four elements, rotation by 2",     ([1, 2, 3, 4], [3, 4, 1, 2]),              True),
        ("Not a rotation (diff values)",     ([1, 2, 3], [4, 5, 6]),                    False),
        ("Repeated values valid rotation",   ([1, 2, 1, 2], [2, 1, 2, 1]),               True),
        ("Repeated values wrong order",      ([1, 1, 2, 2], [1, 2, 1, 2]),              False),
    ],

    "py_constellation_mapper": [
        ("Diagonal pattern",                 ([(0, 0), (1, 1), (2, 2)], 3),             ['*..', '.*.', '..*']),
        ("Cross / plus pattern",             ([(1, 1), (0, 1), (2, 1), (1, 0), (1, 2)], 3),
                                                                                         ['.*.', '***', '.*.']),
        ("Empty star list",                  ([], 2),                                    ['..', '..']),
        ("Duplicate coordinates",            ([(0, 0), (0, 0), (1, 1)], 2),             ['*.', '.*']),
        ("Out-of-bounds ignored",            ([(0, 0), (5, 5)], 3),                     ['*..', '...', '...']),
        ("Horizontal line",                  ([(1, 0), (1, 1), (1, 2)], 3),             ['...', '***', '...']),
        ("Single cell with star",            ([(0, 0)], 1),                              ['*']),
        ("Single cell empty",                ([], 1),                                    ['.']),
        ("Full 2x2 grid",                    ([(0, 0), (0, 1), (1, 0), (1, 1)], 2),     ['**', '**']),
        ("Negative coord ignored",           ([(-1, 0), (0, 0)], 2),                     ['*.', '..']),
        ("Zero grid size",                   ([(0, 0)], 0),                              []),
        ("Negative grid size",               ([(0, 0)], -2),                             []),
    ],

    # ── Exam 04 / Level 2 ─────────────────────────────────────
    "py_list_intersection_finder": [
        ("Three lists, common 2 and 3",      ([[1, 2, 3], [2, 3, 4], [2, 3, 5]],),      [2, 3]),
        ("Shrinking intersection to 4",      ([[1, 2, 3, 4], [2, 4, 6, 8], [4, 8, 12]],), [4]),
        ("No common elements",              ([[1, 2, 3], [4, 5, 6]],),                  []),
        ("Duplicates in input lists",        ([[1, 1, 2, 3], [1, 2, 2, 3], [1, 2, 3, 3]],), [1, 2, 3]),
        ("Empty outer list",                 ([],),                                      []),
        ("One empty sublist",                ([[1, 2, 3], []],),                         []),
        ("Single element list",              ([[5]],),                                   [5]),
        ("Single list passthrough",          ([[1, 2, 3]],),                             [1, 2, 3]),
        ("All same elements",                ([[1, 1, 1], [1, 1]],),                     [1]),
        ("Two identical lists",              ([[1, 2, 3, 4, 5], [1, 2, 3, 4, 5]],),     [1, 2, 3, 4, 5]),
        ("Negative common values",           ([[-5, -3, 0], [-5, -2, 0], [-5, 0]],),    [-5, 0]),
    ],

    "py_merge_sorted_lists": [
        ("Two simple sorted lists",          ([[1, 3, 5], [2, 4, 6]],),                  [1, 2, 3, 4, 5, 6]),
        ("Three sorted lists",               ([[1, 5, 9], [2, 3, 8], [4, 6, 7]],),      [1, 2, 3, 4, 5, 6, 7, 8, 9]),
        ("Different length lists",           ([[5], [1, 3], [2, 4]],),                   [1, 2, 3, 4, 5]),
        ("Preserving duplicates",            ([[1, 1, 2], [2, 3, 3]],),                  [1, 1, 2, 2, 3, 3]),
        ("One empty list",                   ([[], [1, 2, 3]],),                         [1, 2, 3]),
        ("Empty input",                      ([],),                                      []),
        ("Negative numbers",                 ([[-5, -1, 0], [-3, 2, 4]],),               [-5, -3, -1, 0, 2, 4]),
        ("All same values",                  ([[10], [10], [10]],),                       [10, 10, 10]),
        ("Single list passthrough",          ([[1, 2, 3]],),                             [1, 2, 3]),
        ("All empty lists",                  ([[], [], []],),                            []),
    ],

    # ── Exam 04 / Level 3 ─────────────────────────────────────
    "py_package_dependency_resolver": [
        ("Linear dependency chain",          ({"app": ["database"], "database": ["driver"], "driver": []},),
                                             ["driver", "database", "app"]),
        ("Increasing dependencies",          ({"A": [], "B": ["A"], "C": ["A", "B"]},), ["A", "B", "C"]),
        ("Empty input",                      ({},),                                      []),
        ("Circular dependency (2 nodes)",    ({"X": ["Y"], "Y": ["X"]},),                []),
        ("Two independent chains",           ({"web": [], "api": [], "frontend": ["web"], "backend": ["api"]},),
                                             ["api", "web", "backend", "frontend"]),
        ("Single package no deps",           ({"solo": []},),                             ["solo"]),
        ("External dep ignored",             ({"A": ["C"], "B": []},),                    ["A", "B"]),
        ("Three-way circular",               ({"A": ["B"], "B": ["C"], "C": ["A"]},),    []),
        ("Cycle plus independent package",   ({"A": ["B"], "B": ["A"], "C": []},),          []),
        ("Duplicate dependencies",           ({"A": [], "B": ["A", "A"]},),                  ["A", "B"]),
    ],

    "py_palindrome_partitioner": [
        ("'aab' needs 1 cut",                ("aab",),                                   1),
        ("'aba' is a palindrome",            ("aba",),                                   0),
        ("'abcba' is a palindrome",          ("abcba",),                                 0),
        ("'abcd' needs 3 cuts",              ("abcd",),                                  3),
        ("'aabaa' is a palindrome",          ("aabaa",),                                 0),
        ("'abac' needs 1 cut",               ("abac",),                                  1),
        ("Empty string",                     ("",),                                      0),
        ("Single character",                 ("a",),                                     0),
        ("Two different chars",              ("ab",),                                    1),
        ("Two same chars",                   ("aa",),                                    0),
        ("'aabb' needs 1 cut",               ("aabb",),                                  1),
        ("'racecar' is a palindrome",        ("racecar",),                                0),
        ("Multiple possible partitions",     ("ababbbabbababa",),                        3),
    ],

    # ── Exam 04 / Level 4 ─────────────────────────────────────
    "py_sliding_window_maximum": [
        ("Standard case k=3",                ([1, 3, -1, -3, 5, 3, 6, 7], 3),           [3, 3, 5, 5, 6, 7]),
        ("Ascending array k=2",              ([1, 2, 3, 4, 5], 2),                       [2, 3, 4, 5]),
        ("Descending array k=1",             ([5, 4, 3, 2, 1], 1),                       [5, 4, 3, 2, 1]),
        ("Window equals array length",       ([1, 2, 3], 3),                             [3]),
        ("Window larger than array",         ([1, 2, 3], 4),                             []),
        ("Empty array",                      ([], 2),                                    []),
        ("k = 0 (invalid)",                  ([1, 2, 3], 0),                             []),
        ("Single element k=1",               ([1], 1),                                   [1]),
        ("Mixed values with late peak",      ([4, 3, 2, 1, 5], 3),                       [4, 3, 5]),
        ("All identical elements",           ([3, 3, 3, 3], 2),                           [3, 3, 3]),
        ("Negative numbers",                 ([-1, -3, -5, -2], 2),                       [-1, -3, -2]),
        ("Negative k is invalid",            ([1, 2, 3], -1),                             []),
    ],
}


# ══════════════════════════════════════════════════════════════
# Submission Validation
# ══════════════════════════════════════════════════════════════

FORBIDDEN_CALLS = {
    "py_cryptic_sorter": {
        "names": {"sorted"},
        "attributes": {"sort", "sorted"},
    },
}


def validate_submission_rules(exercise_name, file_path):
    """Return an error when a submission uses exercise-specific forbidden APIs."""
    rules = FORBIDDEN_CALLS.get(exercise_name)
    if not rules:
        return None

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as error:
        return (
            f"Syntax Error in your code:\n"
            f"  File \"{error.filename}\", line {error.lineno}\n"
            f"  {error.msg}"
        )
    except OSError as error:
        return f"Could not read your submission:\n  {error}"

    violations = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in rules["names"]:
            violations.add((node.lineno, f"{node.id}()"))
        elif isinstance(node, ast.Attribute) and node.attr in rules["attributes"]:
            violations.add((node.lineno, f".{node.attr}()"))
        elif isinstance(node, ast.alias) and node.name in rules["names"]:
            violations.add((node.lineno, f"{node.name}()"))

    if not violations:
        return None

    details = "\n".join(
        f"  Line {line}: {name} is forbidden"
        for line, name in sorted(violations)
    )
    return (
        "Forbidden function detected in your submission:\n"
        f"{details}\n\n"
        "Implement the sorting algorithm manually without sorted() or .sort()."
    )


def validate_submission_file(exercise_name, func_name):
    """Validate file presence, syntax, required function, and exercise rules."""
    file_path = RENDU_DIR / exercise_name / f"{exercise_name}.py"

    if not file_path.exists():
        return (
            f"File not found:\n"
            f"  {file_path}\n\n"
            f"Please create the directory and file manually:\n"
            f"  rendu/{exercise_name}/{exercise_name}.py"
        )

    rule_error = validate_submission_rules(exercise_name, file_path)
    if rule_error:
        return rule_error

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as error:
        return f"Syntax Error in your code:\n  File \"{error.filename}\", line {error.lineno}\n  {error.msg}"
    except OSError as error:
        return f"Could not read your submission:\n  {error}"

    definitions = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == func_name
    ]
    if not definitions:
        return (
            f"Function '{func_name}' not found in your file.\n"
            f"Make sure you have:\n"
            f"  def {func_name}(...):"
        )
    if isinstance(definitions[-1], ast.AsyncFunctionDef):
        return f"Function '{func_name}' must be declared with 'def', not 'async def'."

    return None


def run_submission_batch(exercise_name, func_name, test_arguments, timeout=FUNCTION_TIMEOUT_SECONDS):
    """Run a complete test batch in one safely terminable child process."""
    file_path = RENDU_DIR / exercise_name / f"{exercise_name}.py"
    if not WORKER_PATH.is_file():
        return None, f"Internal runner not found: {WORKER_PATH.name}"

    command = [sys.executable, "-I", str(WORKER_PATH), str(file_path), func_name]
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            command,
            input=pickle.dumps(test_arguments, protocol=pickle.HIGHEST_PROTOCOL),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(BASE_DIR),
            timeout=timeout,
            creationflags=creation_flags,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, (
            f"TIMEOUT — submission took longer than {timeout}s "
            "(including module initialization)"
        )
    except OSError as error:
        return None, f"Could not start isolated test runner: {error}"

    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr}" if stderr else ""
        return None, f"Isolated test runner exited with code {completed.returncode}{detail}"

    try:
        response = pickle.loads(completed.stdout)
    except Exception:
        return None, "Submission produced an invalid response in the isolated test runner"

    if not isinstance(response, dict) or "ok" not in response:
        return None, "Submission produced an invalid result envelope"
    if not response["ok"]:
        return None, response.get("error", "Unknown submission error")
    results = response.get("results")
    if not isinstance(results, list) or len(results) != len(test_arguments):
        return None, "Submission produced an incomplete test result batch"
    return results, None


def run_submission_isolated(exercise_name, func_name, args, timeout=FUNCTION_TIMEOUT_SECONDS):
    """Run one test through the batch worker (convenience wrapper for diagnostics)."""
    results, error = run_submission_batch(exercise_name, func_name, [args], timeout)
    if error:
        return None, error
    response = results[0]
    if not response.get("ok"):
        return None, response.get("error", "Unknown submission error")
    return response.get("result"), None


def run_with_timeout(func, args, timeout=FUNCTION_TIMEOUT_SECONDS):
    """
    Execute an in-memory function with a timeout (used by internal tests only).

    Returns:
        (result, None) on success
        (None, error_message) on failure or timeout
    """
    result_box = [None]
    error_box = [None]

    def target():
        try:
            result_box[0] = func(*args)
        except BaseException as e:
            error_box[0] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        return None, f"TIMEOUT — function took longer than {timeout}s (possible infinite loop)"
    if error_box[0] is not None:
        e = error_box[0]
        return None, f"{type(e).__name__}: {e}"
    return result_box[0], None


def results_match(result, expected):
    """Compare results strictly, including bool-versus-int and nested types."""
    if type(result) is not type(expected):
        return False
    if isinstance(expected, (list, tuple)):
        return len(result) == len(expected) and all(
            results_match(actual_item, expected_item)
            for actual_item, expected_item in zip(result, expected)
        )
    if isinstance(expected, dict):
        return result.keys() == expected.keys() and all(
            results_match(result[key], expected[key]) for key in expected
        )
    return result == expected


def validate_configuration():
    """Return internal content/configuration problems that would break an exam."""
    errors = []
    registered = set()

    if not WORKER_PATH.is_file():
        errors.append(f"missing isolated runner: {WORKER_PATH.name}")

    for exam_id, exam in EXAMS.items():
        levels = exam.get("levels", {})
        points = exam.get("level_points", {})
        if not levels:
            errors.append(f"{exam_id}: no levels configured")
            continue
        if set(points) != set(levels):
            errors.append(f"{exam_id}: level_points do not match configured levels")
        if sum(points.values()) != 100:
            errors.append(f"{exam_id}: level points total {sum(points.values())}, expected 100")

        for level, exercises in levels.items():
            if not exercises:
                errors.append(f"{exam_id} level {level}: no exercises configured")
            for exercise in exercises:
                name = exercise.get("name")
                func_name = exercise.get("func")
                if not name or not func_name:
                    errors.append(f"{exam_id} level {level}: invalid exercise entry")
                    continue
                if name in registered:
                    errors.append(f"duplicate registered exercise: {name}")
                registered.add(name)
                if name not in SUBJECTS:
                    errors.append(f"{name}: missing subject")
                if name not in SIGNATURES or f"def {func_name}(" not in SIGNATURES[name]:
                    errors.append(f"{name}: missing or incorrect signature")
                tests = TEST_CASES.get(name)
                if not tests:
                    errors.append(f"{name}: no tests configured")
                elif any(not isinstance(test, tuple) or len(test) != 3 for test in tests):
                    errors.append(f"{name}: malformed test case")

    for collection_name, collection in (
        ("subject", SUBJECTS),
        ("signature", SIGNATURES),
        ("test group", TEST_CASES),
    ):
        for orphan in set(collection) - registered:
            errors.append(f"orphan {collection_name}: {orphan}")

    return errors


def grade_exercise(exercise_name, func_name, func=None):
    """
    Grade user's submission against all test cases.

    Returns:
        (passed_count, total_count, detail_string)
    """
    if func is None:
        error = validate_submission_file(exercise_name, func_name)
        if error:
            return 0, 0, error

    tests = TEST_CASES.get(exercise_name, [])
    if not tests:
        return 0, 0, "No test cases found for this exercise."

    passed = 0
    total = len(tests)
    lines = []

    isolated_results = None
    isolated_error = None
    if func is None:
        test_arguments = [copy.deepcopy(args) for _, args, _ in tests]
        isolated_results, isolated_error = run_submission_batch(
            exercise_name,
            func_name,
            test_arguments,
        )

    for i, (desc, args, expected) in enumerate(tests, 1):
        args_copy = copy.deepcopy(args)
        if func is None:
            if isolated_error:
                result, error = None, isolated_error
            else:
                response = isolated_results[i - 1]
                result = response.get("result")
                error = None if response.get("ok") else response.get("error", "Unknown submission error")
        else:
            result, error = run_with_timeout(func, args_copy)
        num_label = f"{i:02d}/{total:02d}"

        if error:
            lines.append(f"  Test {num_label}: {desc:<42s} [FAIL]")
            lines.append(f"           Error: {error}")
        elif results_match(result, expected):
            passed += 1
            lines.append(f"  Test {num_label}: {desc:<42s} [PASS]")
        else:
            args_str = ", ".join(repr(a) for a in args)
            lines.append(f"  Test {num_label}: {desc:<42s} [FAIL]")
            lines.append(f"           Call:     {func_name}({args_str})")
            lines.append(f"           Expected: {repr(expected)}")
            lines.append(f"           Got:      {repr(result)}")

    return passed, total, "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Workspace Management
# ══════════════════════════════════════════════════════════════

def get_plain_subject(exercise_name):
    """Return an exercise subject without README/Markdown wrappers."""
    subject = SUBJECTS.get(exercise_name, f"{exercise_name}\n\n(No subject available)\n")
    lines = subject.splitlines()
    if lines and lines[0].lstrip().startswith("#"):
        lines = lines[1:]
    lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(lines).strip() + "\n"


def cleanup_workspace():
    """Remove subject/, rendu/, and traces/ directories completely after exam."""
    if SUBJECT_DIR.exists():
        shutil.rmtree(SUBJECT_DIR, ignore_errors=True)
    if RENDU_DIR.exists():
        shutil.rmtree(RENDU_DIR, ignore_errors=True)
    if TRACES_DIR.exists():
        shutil.rmtree(TRACES_DIR, ignore_errors=True)


def prepare_exercise_environment(exercise_name):
    """
    Set up the workspace for the newly assigned exercise:
    - Ensures empty rendu/ directory exists (user creates exercise subfolders manually)
    - Creates subject/<exercise_name>/<exercise_name>.txt
    - Keeps previously assigned subjects so all subjects for the exam are saved
    """
    RENDU_DIR.mkdir(parents=True, exist_ok=True)
    SUBJECT_DIR.mkdir(parents=True, exist_ok=True)

    ex_subj_dir = SUBJECT_DIR / exercise_name
    ex_subj_dir.mkdir(parents=True, exist_ok=True)

    subject_text = get_plain_subject(exercise_name)
    (ex_subj_dir / f"{exercise_name}.txt").write_text(subject_text, encoding="utf-8")


# ══════════════════════════════════════════════════════════════
# Exam Shell Engine
# ══════════════════════════════════════════════════════════════

class ExamShell:
    """
    The main interactive exam simulator.
    """

    def __init__(self, exam_config, practice_mode=False, practice_selection=None):
        self.config = exam_config
        self.exam_name = exam_config["name"]
        self.exam_title = exam_config["title"]
        self.levels = exam_config["levels"]
        self.level_points = exam_config["level_points"]

        self.practice_mode = practice_mode
        self.start_time = None
        self.end_time = None
        self.current_level = practice_selection[0] if practice_selection else 1
        self.current_exercise = None
        self.initial_exercise = practice_selection[1] if practice_selection else None
        self.score = 0
        self.max_level = max(self.levels.keys())
        self.attempts = 0
        self.attempts_by_exercise = {}
        self.exercises_passed = []
        self.finished = False

    def time_remaining(self):
        if self.practice_mode:
            return None
        remaining = self.end_time - datetime.now()
        if remaining.total_seconds() <= 0:
            return timedelta(0)
        return remaining

    def format_time(self, td):
        if td is None:
            return "PRACTICE (No Timer)"
        total = int(td.total_seconds())
        if total <= 0:
            return "TIME EXPIRED"
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}h {m:02d}m {s:02d}s"

    def is_expired(self):
        if self.practice_mode:
            return False
        return datetime.now() >= self.end_time

    def pick_exercise(self, level):
        available = self.levels.get(level, [])
        if not available:
            return None
        return random.choice(available)

    def print_banner(self):
        t_str = self.format_time(self.time_remaining())
        t_color = C.G if self.practice_mode else (C.R if (self.time_remaining() and self.time_remaining().total_seconds() < 900) else C.Y)

        print(f"{C.B}{C.CY}╔══════════════════════════════════════════════════════════════╗{C.RST}")
        print(f"{C.B}{C.CY}║{C.RST}  {C.B}{self.exam_title:<45s}{C.RST}     {C.B}{C.CY}║{C.RST}")
        print(f"{C.B}{C.CY}╠══════════════════════════════════════════════════════════════╣{C.RST}")
        if self.practice_mode:
            print(f"{C.B}{C.CY}║{C.RST}  Level: {C.B}{self.current_level}/{self.max_level}{C.RST}  │  Solved: {C.B}{C.G}{len(self.exercises_passed):<3d}{C.RST}  │  Time: {t_color}{t_str:<22s}{C.RST}{C.B}{C.CY}║{C.RST}")
        else:
            print(f"{C.B}{C.CY}║{C.RST}  Level: {C.B}{self.current_level}/{self.max_level}{C.RST}  │  Score: {C.B}{C.G}{self.score}/100{C.RST}  │  Time: {t_color}{t_str:<22s}{C.RST}{C.B}{C.CY}║{C.RST}")
        print(f"{C.B}{C.CY}╚══════════════════════════════════════════════════════════════╝{C.RST}")

    def assign_exercise(self, exercise=None):
        self.current_exercise = exercise or self.pick_exercise(self.current_level)
        exercise_name = self.current_exercise["name"]
        self.attempts = self.attempts_by_exercise.get(exercise_name, 0)

        # Auto-setup subject/ and template in rendu/
        prepare_exercise_environment(self.current_exercise["name"])

        clear()
        self.print_banner()

        ex_name = self.current_exercise["name"]
        func_name = self.current_exercise["func"]
        rendu_path = f"rendu/{ex_name}/{ex_name}.py"
        subject_path = f"subject/{ex_name}/{ex_name}.txt"

        print()
        print(f"  {C.B}{C.M}══════════ NEW ASSIGNMENT: Level {self.current_level} ══════════{C.RST}")
        print()
        print(f"  Exercise:   {C.B}{C.W}{ex_name}{C.RST}")
        print(f"  Function:   {C.CY}{func_name}(){C.RST}")
        print(f"  Subject:    {C.Y}{subject_path}{C.RST}")
        print(f"  Submit at:  {C.G}{rendu_path}{C.RST} {C.DIM}(create folder & file manually){C.RST}")
        if self.practice_mode:
            print(f"  Mode:       {C.G}Free practice (no score){C.RST}")
        else:
            print(f"  Points:     {C.B}+{self.level_points.get(self.current_level, 0)} pts{C.RST} on pass")
        print()
        print(f"  {C.DIM}------------------------------------------------------------{C.RST}")
        print(f"  {C.DIM}Subject preview:{C.RST}")
        print()
        self.cmd_subject()
        print()
        print(f"  {C.DIM}------------------------------------------------------------{C.RST}")
        print(f"  Type {C.B}'grademe'{C.RST} to submit your solution when ready.")
        print()

    def cmd_subject(self):
        if not self.current_exercise:
            print(f"  {C.DIM}No exercise currently assigned.{C.RST}")
            return
        subject = get_plain_subject(self.current_exercise["name"])
        for line in subject.splitlines():
            print(f"  {line}")

    def cmd_status(self):
        clear()
        self.print_banner()
        print()
        if self.current_exercise:
            ex_name = self.current_exercise["name"]
            print(f"  Current Exercise : {C.B}{ex_name}{C.RST}")
            print(f"  Function Name    : {C.CY}{self.current_exercise['func']}(){C.RST}")
            print(f"  Solution Path    : {C.G}rendu/{ex_name}/{ex_name}.py{C.RST} {C.DIM}(create manually){C.RST}")
            print(f"  Subject Path     : {C.Y}subject/{ex_name}/{ex_name}.txt{C.RST}")
            print(f"  Attempts so far  : {self.attempts}")
        if self.exercises_passed:
            print(f"\n  {C.G}Completed Exercises:{C.RST}")
            for lvl, name, score in self.exercises_passed:
                points = "" if self.practice_mode else f" (+{score} pts)"
                print(f"    ✓ Level {lvl}: {name}{points}")
        print()

    def cmd_time(self):
        if self.practice_mode:
            print(f"\n  {C.G}Practice Mode — No time limit.{C.RST}\n")
        else:
            rem = self.time_remaining()
            print(f"\n  Time remaining: {C.B}{self.format_time(rem)}{C.RST}\n")

    def cmd_help(self):
        print(f"\n  {C.B}Available Commands:{C.RST}")
        print(f"    {C.G}grademe{C.RST}     - Submit and test your solution for {C.CY}{self.current_exercise['func'] if self.current_exercise else ''}(){C.RST}")
        print(f"    {C.G}subject{C.RST}     - Display the subject in terminal")
        print(f"    {C.G}trace{C.RST} [n]   - Display the latest test trace (or attempt n) in terminal")
        print(f"    {C.G}status{C.RST}      - Show your exam status and score")
        print(f"    {C.G}time{C.RST}        - Show remaining time")
        print(f"    {C.G}clear{C.RST}       - Clear terminal screen")
        if self.practice_mode:
            print(f"    {C.G}menu{C.RST}        - Choose another level and exercise")
        print(f"    {C.G}help{C.RST}        - Show this command list")
        exit_description = "Finish the practice session" if self.practice_mode else "Abandon and quit the exam"
        print(f"    {C.R}exit{C.RST}        - {exit_description}\n")

    def cmd_practice_menu(self):
        """Let the user switch exercises freely while practicing."""
        selection = select_practice_exercise_menu(self.config)
        if selection is None:
            self.finish_exam(success=False)
            return

        self.current_level, exercise = selection
        self.assign_exercise(exercise)

    def cmd_trace(self, arg=None):
        if not TRACES_DIR.exists():
            print(f"\n  {C.DIM}No traces available yet. Run 'grademe' first.{C.RST}\n")
            return

        target_file = None
        if arg:
            arg_str = str(arg).strip()
            if arg_str.isdigit() and self.current_exercise:
                target_file = TRACES_DIR / f"{self.current_exercise['name']}_trace_{arg_str}.txt"
            elif Path(arg_str).name == arg_str:
                candidate = TRACES_DIR / arg_str
                if candidate.is_file():
                    target_file = candidate

        if not target_file or not target_file.exists():
            if self.current_exercise and self.attempts > 0:
                target_file = TRACES_DIR / f"{self.current_exercise['name']}_trace_{self.attempts}.txt"

            if not target_file or not target_file.exists():
                trace_files = sorted(TRACES_DIR.glob("*_trace_*.txt"), key=lambda f: f.stat().st_mtime)
                if trace_files:
                    target_file = trace_files[-1]

        if not target_file or not target_file.exists():
            print(f"\n  {C.DIM}No trace available yet. Run 'grademe' first.{C.RST}\n")
            return

        print()
        print(f"  {C.DIM}Displaying {target_file.name}:{C.RST}")
        print(target_file.read_text(encoding="utf-8"))
        print()

    def cmd_grademe(self):
        if not self.current_exercise:
            print(f"  {C.R}No exercise assigned.{C.RST}")
            return

        ex_name = self.current_exercise["name"]
        func_name = self.current_exercise["func"]

        # Validate source without importing untrusted user code into the exam shell.
        error = validate_submission_file(ex_name, func_name)
        if error:
            print(f"\n  {C.R}Error:{C.RST}")
            for line in error.splitlines():
                print(f"    {line}")
            print(f"\n  {C.Y}Create/edit your code in {C.G}rendu/{ex_name}/{ex_name}.py{C.Y} and try again.{C.RST}\n")
            return

        # Increment attempt counter only for valid code evaluations that run tests
        self.attempts += 1
        self.attempts_by_exercise[ex_name] = self.attempts

        print()
        print(f"  {C.CY}Grading {ex_name} (attempt #{self.attempts})...{C.RST}")
        print(f"  {C.DIM}Running isolated test batch ({FUNCTION_TIMEOUT_SECONDS}s safety timeout)...{C.RST}")
        print()

        passed, total, details = grade_exercise(ex_name, func_name)

        if total == 0:
            print(f"  {C.R}Error:{C.RST}")
            for line in details.splitlines():
                print(f"    {line}")
            print(f"\n  {C.Y}Create/edit your code in {C.G}rendu/{ex_name}/{ex_name}.py{C.Y} and try again.{C.RST}\n")
            return

        # Write numbered trace file for this grademe attempt
        TRACES_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_word = "SUCCESS" if passed == total else "FAILURE"
        trace_filename = f"{ex_name}_trace_{self.attempts}.txt"
        trace_file = TRACES_DIR / trace_filename

        trace_content = (
            f"{'=' * 70}\n"
            f"EXAM SHELL TRACE - {ex_name} (Attempt #{self.attempts})\n"
            f"Date:   {timestamp}\n"
            f"Status: {status_word} ({passed}/{total} tests passed)\n"
            f"{'=' * 70}\n\n"
            f"{details}\n\n"
            f"{'=' * 70}\n"
            f"Summary: {passed}/{total} tests passed.\n"
            f"{'=' * 70}\n"
        )

        trace_file.write_text(trace_content, encoding="utf-8")

        if passed == total:
            if self.practice_mode:
                completed = (self.current_level, ex_name, 0)
                if not any(level == self.current_level and name == ex_name
                           for level, name, _ in self.exercises_passed):
                    self.exercises_passed.append(completed)

                print(f"  {C.BG_G}{C.W}{C.B}  SUCCESS! ALL {total}/{total} TESTS PASSED!  {C.RST}")
                print(f"  {C.G}Exercise completed in practice mode.{C.RST}")
                print(f"  {C.DIM}Trace saved to: traces/{trace_filename}{C.RST}\n")
                try:
                    input(f"  {C.B}Press [Enter] to choose another exercise...{C.RST} ")
                except (EOFError, KeyboardInterrupt):
                    self.finish_exam(success=True)
                    return

                self.cmd_practice_menu()
                return

            lvl_pts = self.level_points.get(self.current_level, 0)
            self.score += lvl_pts
            self.exercises_passed.append((self.current_level, ex_name, lvl_pts))

            print(f"  {C.BG_G}{C.W}{C.B}  SUCCESS! ALL {total}/{total} TESTS PASSED!  {C.RST}")
            print(f"  {C.G}+{lvl_pts} points awarded! Current score: {self.score}/100{C.RST}")
            print(f"  {C.DIM}Trace saved to: traces/{trace_filename}{C.RST}\n")

            if self.current_level >= self.max_level:
                self.finish_exam(success=True)
            else:
                self.current_level += 1
                try:
                    input_until(
                        f"  {C.B}Press [Enter] to proceed to Level {self.current_level}...{C.RST} ",
                        self.end_time,
                    )
                except TimeoutError:
                    print(f"\n  {C.BG_R}{C.W}{C.B}  TIME IS UP! Exam duration expired.  {C.RST}\n")
                    self.finish_exam(success=False)
                    return
                except (EOFError, KeyboardInterrupt):
                    pass
                self.assign_exercise()
        else:
            print(f"  {C.BG_R}{C.W}{C.B}  FAILURE: Your code is incorrect!  {C.RST}")
            print(f"  {C.R}Some tests failed. You can check the traces for details:{C.RST}")
            print(f"    {C.CY}traces/{trace_filename}{C.RST}  (or type {C.B}'trace'{C.RST} here)")
            print()
            print(f"  {C.DIM}Edit your code in {C.G}rendu/{ex_name}/{ex_name}.py{C.DIM} and type 'grademe' to re-test.{C.RST}\n")

    def finish_exam(self, success=False):
        self.finished = True
        clear()

        if self.practice_mode:
            print(f"\n{C.B}{C.G}PRACTICE SESSION FINISHED{C.RST}")
            if self.start_time:
                elapsed = datetime.now() - self.start_time
                print(f"\n  Time Practiced: {str(elapsed).split('.')[0]}")
            print(f"  Exercises Solved: {len(self.exercises_passed)}")
            if self.exercises_passed:
                print(f"\n  {C.B}Completed Exercises:{C.RST}")
                for level, name, _ in self.exercises_passed:
                    print(f"    Level {level}: {name}")
            cleanup_workspace()
            print(f"\n  {C.DIM}Cleaned up subject/, rendu/, and traces/ directories.{C.RST}\n")
            return

        print()
        if success:
            print(f"{C.B}{C.G}╔══════════════════════════════════════════════════════════════╗{C.RST}")
            print(f"{C.B}{C.G}║               CONGRATULATIONS! EXAM PASSED!                 ║{C.RST}")
            print(f"{C.B}{C.G}╚══════════════════════════════════════════════════════════════╝{C.RST}")
        else:
            print(f"{C.B}{C.R}╔══════════════════════════════════════════════════════════════╗{C.RST}")
            print(f"{C.B}{C.R}║                      EXAM FINISHED                           ║{C.RST}")
            print(f"{C.B}{C.R}╚══════════════════════════════════════════════════════════════╝{C.RST}")

        print(f"\n  Exam:        {self.exam_title}")
        print(f"  Final Score: {C.B}{self.score}/100{C.RST}")
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            print(f"  Time Taken:  {str(elapsed).split('.')[0]}")

        print(f"\n  {C.B}Completed Exercises:{C.RST}")
        if self.exercises_passed:
            for lvl, name, pts in self.exercises_passed:
                print(f"    ✓ Level {lvl}: {name} ({pts} pts)")
        else:
            print(f"    {C.DIM}None{C.RST}")

        # Clean up subject/, rendu/, and traces/ folders completely after exam
        cleanup_workspace()
        print(f"\n  {C.DIM}Cleaned up subject/, rendu/, and traces/ directories.{C.RST}")
        print()

    def run(self):
        clear()
        mode_str = f"{C.G}PRACTICE MODE (No Timer){C.RST}" if self.practice_mode else f"{C.Y}{EXAM_DURATION_HOURS} HOURS TIMED EXAM{C.RST}"

        print(f"{C.B}{C.CY}╔══════════════════════════════════════════════════════════════╗{C.RST}")
        print(f"{C.B}{C.CY}║                     EXAM SHELL v2.0                         ║{C.RST}")
        print(f"{C.B}{C.CY}║              42-Style Python Exam Simulator                 ║{C.RST}")
        print(f"{C.B}{C.CY}╚══════════════════════════════════════════════════════════════╝{C.RST}\n")
        print(f"  {C.B}Exam:{C.RST}       {self.exam_title}")
        print(f"  {C.B}Mode:{C.RST}       {mode_str}")
        print(f"  {C.B}Levels:{C.RST}     {self.max_level} Levels ({sum(len(v) for v in self.levels.values())} total exercises pool)")
        print(f"  {C.B}Subjects:{C.RST}   Saved in {C.Y}subject/<exercise>/<exercise>.txt{C.RST}")
        print(f"  {C.B}Workspace:{C.RST}  Create {C.G}rendu/<exercise>/<exercise>.py{C.RST} manually")
        print(f"  {C.B}Submit:{C.RST}     Type {C.B}'grademe'{C.RST} to test your code")
        print()
        print(f"  {C.B}Rules:{C.RST}")
        if self.practice_mode:
            print(f"    • Choose any level and exercise; use 'menu' to switch at any time.")
        else:
            print(f"    • Pass all test cases for an exercise to advance to the next level.")
        print(f"    • On failure, you can modify your code and resubmit with 'grademe'.")
        print(f"    • Tests include subject examples + hidden edge cases.")
        print(f"    • Each complete grade run has a {FUNCTION_TIMEOUT_SECONDS}-second safety timeout.")
        print(f"    • Session files are automatically cleaned when you finish.")
        print()

        try:
            session_name = "practice session" if self.practice_mode else "exam"
            input(f"  {C.B}Press [Enter] to begin the {session_name}...{C.RST} ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        cleanup_workspace()

        try:
            self.start_time = datetime.now()
            self.end_time = self.start_time + timedelta(hours=EXAM_DURATION_HOURS)

            self.assign_exercise(self.initial_exercise)

            while not self.finished:
                if self.is_expired():
                    print(f"\n  {C.BG_R}{C.W}{C.B}  TIME IS UP! Exam duration expired.  {C.RST}\n")
                    self.finish_exam(success=False)
                    break

                prompt_time = self.format_time(self.time_remaining())
                prompt_str = f"[{prompt_time}] examshell> "

                try:
                    deadline = None if self.practice_mode else self.end_time
                    cmd = input_until(f"{C.CY}{prompt_str}{C.RST}", deadline).strip().lower()
                except TimeoutError:
                    print(f"\n  {C.BG_R}{C.W}{C.B}  TIME IS UP! Exam duration expired.  {C.RST}\n")
                    self.finish_exam(success=False)
                    break
                except (EOFError, KeyboardInterrupt):
                    print("\nInput closed; finishing the session.")
                    self.finish_exam(success=False)
                    break

                if not cmd:
                    continue

                cmd_parts = cmd.split()
                main_cmd = cmd_parts[0]
                cmd_arg = cmd_parts[1] if len(cmd_parts) > 1 else None

                if main_cmd in ("grademe", "grade"):
                    self.cmd_grademe()
                elif main_cmd == "subject":
                    print()
                    self.cmd_subject()
                    print()
                elif main_cmd in ("trace", "traces"):
                    self.cmd_trace(cmd_arg)
                elif main_cmd == "status":
                    self.cmd_status()
                elif main_cmd == "time":
                    self.cmd_time()
                elif main_cmd == "clear":
                    clear()
                    self.print_banner()
                    print()
                elif main_cmd == "menu" and self.practice_mode:
                    self.cmd_practice_menu()
                elif main_cmd == "help":
                    self.cmd_help()
                elif cmd in ("exit", "quit"):
                    try:
                        action = "finish the practice session" if self.practice_mode else "abandon the exam"
                        deadline = None if self.practice_mode else self.end_time
                        confirm = input_until(
                            f"  {C.R}Are you sure you want to {action}? (y/N): {C.RST}",
                            deadline,
                        ).strip().lower()
                        if confirm in ("y", "yes"):
                            self.finish_exam(success=False)
                            break
                    except TimeoutError:
                        print(f"\n  {C.BG_R}{C.W}{C.B}  TIME IS UP! Exam duration expired.  {C.RST}\n")
                        self.finish_exam(success=False)
                        break
                    except (EOFError, KeyboardInterrupt):
                        pass
                else:
                    print(f"  Unknown command: '{cmd}'. Type {C.B}'help'{C.RST} for available commands.")
        finally:
            cleanup_workspace()


# ══════════════════════════════════════════════════════════════
# Exam Selection Menu
# ══════════════════════════════════════════════════════════════

MENU_INNER_WIDTH = 66


def print_setup_header(step, title, subtitle):
    """Print the shared header used by every interactive setup screen."""
    print(f"{C.B}{C.CY}╔{'═' * (MENU_INNER_WIDTH + 2)}╗{C.RST}")
    print(f"{C.B}{C.CY}║ {title.center(MENU_INNER_WIDTH)} ║{C.RST}")
    print(f"{C.B}{C.CY}║ {subtitle.center(MENU_INNER_WIDTH)} ║{C.RST}")
    print(f"{C.B}{C.CY}╚{'═' * (MENU_INNER_WIDTH + 2)}╝{C.RST}")
    setup_paths = {
        1: "EXAM",
        2: "EXAM  ›  MODE",
        3: "EXAM  ›  MODE  ›  LEVEL",
        4: "EXAM  ›  MODE  ›  LEVEL  ›  EXERCISE",
    }
    print(f"\n  {C.DIM}SETUP  ›  {setup_paths.get(step, '')}{C.RST}\n")


def print_menu_option(key, title, description, details=None):
    """Print one consistent, easy-to-scan menu option."""
    print(f"  {C.G}{C.B}[{key}]{C.RST}  {C.B}{title}{C.RST}")
    print(f"       {description}")
    if details:
        print(f"       {C.DIM}{details}{C.RST}")
    print()


def print_menu_navigation(back_label=None, quit_label="Quit"):
    """Print navigation shortcuts at the bottom of a menu."""
    shortcuts = []
    if back_label:
        shortcuts.append(f"{C.Y}[B]{C.RST} {back_label}")
    shortcuts.append(f"{C.R}[Q]{C.RST} {quit_label}")
    print(f"  {'    '.join(shortcuts)}\n")


def select_mode_menu(exam_config):
    """Choose between the timed exam and free practice modes."""
    clear()
    print_setup_header(2, "CHOOSE YOUR MODE", exam_config["name"])
    print(f"  How would you like to train today?\n")
    print_menu_option(
        "1",
        "REAL EXAM",
        "Simulates the real 42 exam experience.",
        f"{EXAM_DURATION_HOURS}-hour timer  •  random exercises  •  level progression",
    )
    print_menu_option(
        "2",
        "PRACTICE",
        "Work on any exercise at your own pace.",
        "no timer  •  choose level  •  switch exercises anytime",
    )
    print_menu_navigation("Back to exams", "Quit setup")

    while True:
        try:
            choice = input(f"  {C.CY}{C.B}Your choice [1-2]: {C.RST}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return None

        if choice in ("1", "real", "exam", "real exam"):
            return "real"
        if choice in ("2", "practice", "practise"):
            return "practice"
        if choice in ("b", "back"):
            return "back"
        if choice in ("q", "quit", "exit"):
            print("\nExiting.")
            return None
        print(f"  {C.R}Enter 1 for Real Exam, 2 for Practice, B to go back, or Q to quit.{C.RST}")


def select_practice_exercise_menu(exam_config, allow_mode_back=False):
    """Return a freely selected (level, exercise) pair for practice."""
    levels = exam_config["levels"]

    while True:
        clear()
        print_setup_header(3, "CHOOSE A LEVEL", f"{exam_config['name']}  •  Practice")
        print(f"  Pick a level. You can change it later with the {C.B}menu{C.RST} command.\n")
        for level in sorted(levels):
            level_exercises = levels[level]
            exercise_count = len(level_exercises)
            suffix = "exercise" if exercise_count == 1 else "exercises"
            exercise_names = "  •  ".join(exercise["name"] for exercise in level_exercises)
            print_menu_option(
                str(level),
                f"LEVEL {level}",
                f"{exercise_count} {suffix}",
                exercise_names,
            )
        back_label = "Back to mode" if allow_mode_back else None
        print_menu_navigation(back_label, "Finish practice")

        while True:
            try:
                choice = input(f"  {C.CY}{C.B}Choose a level: {C.RST}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return None

            if choice in ("q", "quit", "exit"):
                return None
            if allow_mode_back and choice in ("b", "back"):
                return "back"
            if choice.startswith("level"):
                choice = choice[5:].strip()
            if choice.isdigit() and int(choice) in levels:
                break
            valid_levels = ", ".join(map(str, sorted(levels)))
            navigation_hint = ", B to go back" if allow_mode_back else ""
            print(f"  {C.R}Please choose level {valid_levels}{navigation_hint}, or Q to finish.{C.RST}")

        level = int(choice)
        exercises = levels[level]

        clear()
        print_setup_header(4, "CHOOSE AN EXERCISE", f"{exam_config['name']}  •  Practice  •  Level {level}")
        print(f"  Select the exercise you want to solve.\n")
        for index, exercise in enumerate(exercises, start=1):
            print_menu_option(
                str(index),
                exercise["name"],
                f"Required function: {C.CY}{exercise['func']}(){C.RST}",
                f"Submit: rendu/{exercise['name']}/{exercise['name']}.py",
            )
        print_menu_navigation("Back to levels", "Finish practice")

        while True:
            try:
                exercise_choice = input(
                    f"  {C.CY}{C.B}Choose an exercise [1-{len(exercises)}]: {C.RST}"
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                return None

            if exercise_choice in ("b", "back"):
                break
            if exercise_choice in ("q", "quit", "exit"):
                return None
            if exercise_choice.isdigit() and 1 <= int(exercise_choice) <= len(exercises):
                return level, exercises[int(exercise_choice) - 1]
            print(
                f"  {C.R}Please enter a number from 1 to {len(exercises)}, "
                f"B to go back, or Q to finish.{C.RST}"
            )


def select_exam_menu():
    """Display interactive exam selection menu."""
    clear()
    print_setup_header(1, "WELCOME TO EXAM SHELL", "42-Style Python Exam Simulator")
    print(f"  First, choose the exam you want to work on.\n")

    exam_ids = list(EXAMS)
    for index, exam_id in enumerate(exam_ids, start=1):
        config = EXAMS[exam_id]
        level_count = len(config["levels"])
        exercise_count = sum(len(exercises) for exercises in config["levels"].values())
        description = config["title"].split("—", 1)[-1].strip()
        print_menu_option(
            str(index),
            config["name"].upper(),
            description,
            f"{level_count} levels  •  {exercise_count} exercises  •  {EXAM_DURATION_HOURS}-hour real mode",
        )
    print_menu_navigation(quit_label="Quit")

    while True:
        try:
            choice = input(f"  {C.CY}{C.B}Your choice [1-{len(exam_ids)}]: {C.RST}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            sys.exit(0)

        aliases = {
            "1": "exam03", "3": "exam03", "03": "exam03",
            "exam 03": "exam03", "exam 3": "exam03", "exam03": "exam03",
            "2": "exam04", "4": "exam04", "04": "exam04",
            "exam 04": "exam04", "exam 4": "exam04", "exam04": "exam04",
        }
        if choice in aliases:
            return aliases[choice]
        if choice in ("q", "quit", "exit"):
            print("\nExiting.")
            sys.exit(0)
        print(f"  {C.R}Please enter 1 for Exam 03, 2 for Exam 04, or Q to quit.{C.RST}")


# ══════════════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════════════

def main():
    configuration_errors = validate_configuration()
    if configuration_errors:
        print(f"{C.R}{C.B}Exam Shell configuration error:{C.RST}")
        for error in configuration_errors:
            print(f"  - {error}")
        return

    exam_id = None
    if "--exam" in sys.argv:
        try:
            idx = sys.argv.index("--exam")
            val = sys.argv[idx + 1].strip().lower()
            if val in ("3", "03", "exam03", "exam 03"):
                exam_id = "exam03"
            elif val in ("4", "04", "exam04", "exam 04"):
                exam_id = "exam04"
        except (IndexError, ValueError):
            pass

    if "--practice" in sys.argv:
        forced_mode = "practice"
    elif "--real" in sys.argv or "--timed" in sys.argv:
        forced_mode = "real"
    else:
        forced_mode = None

    while True:
        if not exam_id:
            exam_id = select_exam_menu()
        config = EXAMS[exam_id]

        while True:
            mode = forced_mode or select_mode_menu(config)
            if mode == "back":
                exam_id = None
                break
            if mode is None:
                return

            practice_mode = mode == "practice"
            practice_selection = None
            if practice_mode:
                practice_selection = select_practice_exercise_menu(
                    config,
                    allow_mode_back=forced_mode is None,
                )
                if practice_selection == "back":
                    continue
                if practice_selection is None:
                    return

            shell = ExamShell(
                config,
                practice_mode=practice_mode,
                practice_selection=practice_selection,
            )
            shell.run()
            return


if __name__ == "__main__":
    main()
