import heapq
import shutil
import time
import unittest
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import examshell


def bracket_validator(text):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for char in text:
        if char in "([{":
            stack.append(char)
        elif char in pairs and (not stack or stack.pop() != pairs[char]):
            return False
    return not stack


def cryptic_sorter(strings):
    return sorted(strings, key=lambda value: (len(value), value.lower()))


def echo_validator(text):
    letters = "".join(char.lower() for char in text if char.isalpha())
    return bool(letters) and letters == letters[::-1]


def mirror_matrix(matrix):
    return [row[::-1] for row in matrix]


def hidenp(small, big):
    iterator = iter(big)
    return all(char in iterator for char in small)


def inter(first, second):
    return "".join(dict.fromkeys(char for char in first if char in second))


def number_base_converter(number, from_base, to_base):
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if not number or not 2 <= from_base <= 36 or not 2 <= to_base <= 36:
        return "ERROR"
    value = 0
    for char in number.upper():
        digit = digits.find(char)
        if digit < 0 or digit >= from_base:
            return "ERROR"
        value = value * from_base + digit
    if value == 0:
        return "0"
    result = ""
    while value:
        result = digits[value % to_base] + result
        value //= to_base
    return result


def pattern_tracker(text):
    return sum(
        first.isdigit() and second.isdigit() and int(second) == int(first) + 1
        for first, second in zip(text, text[1:])
    )


def anagram(first, second):
    normalize = lambda value: Counter(char.lower() for char in value if char != " ")
    return normalize(first) == normalize(second)


def shadow_merge(first, second):
    result = []
    left = right = 0
    while left < len(first) and right < len(second):
        if first[left] <= second[right]:
            result.append(first[left])
            left += 1
        else:
            result.append(second[right])
            right += 1
    return result + first[left:] + second[right:]


def string_permutation_checker(first, second):
    return Counter(first) == Counter(second)


def string_sculptor(text):
    result = []
    letter_index = 0
    for char in text:
        if char == " ":
            result.append(char)
            letter_index = 0
        elif char.isalpha():
            result.append(char.lower() if letter_index % 2 == 0 else char.upper())
            letter_index += 1
        else:
            result.append(char)
    return "".join(result)


def twist_sequence(values, shift):
    if not values:
        return []
    shift %= len(values)
    return values[-shift:] + values[:-shift] if shift else values[:]


def whisper_cipher(text, shift):
    result = []
    for char in text:
        if "a" <= char <= "z":
            result.append(chr((ord(char) - ord("a") + shift) % 26 + ord("a")))
        elif "A" <= char <= "Z":
            result.append(chr((ord(char) - ord("A") + shift) % 26 + ord("A")))
        else:
            result.append(char)
    return "".join(result)


def array_rotation_detector(first, second):
    return len(first) == len(second) and (
        not first or any(first[index:] + first[:index] == second for index in range(len(first)))
    )


def constellation_mapper(stars, size):
    grid = [["."] * size for _ in range(max(0, size))]
    for row, column in stars:
        if 0 <= row < size and 0 <= column < size:
            grid[row][column] = "*"
    return ["".join(row) for row in grid]


def list_intersection_finder(lists):
    if not lists or any(not values for values in lists):
        return []
    common = set(lists[0])
    for values in lists[1:]:
        common.intersection_update(values)
    return sorted(common)


def merge_sorted_lists(lists):
    return list(heapq.merge(*lists))


def package_dependency_resolver(packages):
    remaining = {
        package: {dependency for dependency in dependencies if dependency in packages}
        for package, dependencies in packages.items()
    }
    result = []
    while remaining:
        ready = sorted(package for package, dependencies in remaining.items() if not dependencies)
        if not ready:
            return []
        result.extend(ready)
        for package in ready:
            del remaining[package]
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    return result


def palindrome_partitioner(text):
    if not text:
        return 0
    cuts = list(range(len(text)))
    for end in range(len(text)):
        for start in range(end + 1):
            candidate = text[start:end + 1]
            if candidate == candidate[::-1]:
                cuts[end] = 0 if start == 0 else min(cuts[end], cuts[start - 1] + 1)
    return cuts[-1]


def sliding_window_maximum(values, size):
    if size <= 0 or size > len(values):
        return []
    return [max(values[index:index + size]) for index in range(len(values) - size + 1)]


REFERENCE_FUNCTIONS = {
    "py_bracket_validator": bracket_validator,
    "py_cryptic_sorter": cryptic_sorter,
    "py_echo_validator": echo_validator,
    "py_mirror_matrix": mirror_matrix,
    "py_hidenp": hidenp,
    "py_inter": inter,
    "py_number_base_converter": number_base_converter,
    "py_pattern_tracker": pattern_tracker,
    "py_anagram": anagram,
    "py_shadow_merge": shadow_merge,
    "py_string_permutation_checker": string_permutation_checker,
    "py_string_sculptor": string_sculptor,
    "py_twist_sequence": twist_sequence,
    "py_whisper_cipher": whisper_cipher,
    "py_array_rotation_detector": array_rotation_detector,
    "py_constellation_mapper": constellation_mapper,
    "py_list_intersection_finder": list_intersection_finder,
    "py_merge_sorted_lists": merge_sorted_lists,
    "py_package_dependency_resolver": package_dependency_resolver,
    "py_palindrome_partitioner": palindrome_partitioner,
    "py_sliding_window_maximum": sliding_window_maximum,
}


class ContentTests(unittest.TestCase):
    def test_configuration_is_complete(self):
        self.assertEqual(examshell.validate_configuration(), [])
        self.assertEqual(len(REFERENCE_FUNCTIONS), 21)

    def test_reference_implementations_pass_every_declared_test(self):
        registry = {
            exercise["name"]: exercise["func"]
            for exam in examshell.EXAMS.values()
            for exercises in exam["levels"].values()
            for exercise in exercises
        }
        for exercise_name, reference in REFERENCE_FUNCTIONS.items():
            with self.subTest(exercise=exercise_name):
                passed, total, details = examshell.grade_exercise(
                    exercise_name,
                    registry[exercise_name],
                    func=reference,
                )
                self.assertEqual((passed, total), (total, total), details)

    def test_result_comparison_is_type_strict(self):
        self.assertFalse(examshell.results_match(1, True))
        self.assertFalse(examshell.results_match([1], [True]))
        self.assertTrue(examshell.results_match([1, [2]], [1, [2]]))

    def test_expired_input_deadline_does_not_wait(self):
        with self.assertRaises(TimeoutError):
            examshell.input_until("", datetime.now() - timedelta(seconds=1))

    def test_practice_attempt_counts_survive_exercise_switches(self):
        first = examshell.EXAMS["exam03"]["levels"][1][0]
        second = examshell.EXAMS["exam03"]["levels"][1][1]
        shell = examshell.ExamShell(
            examshell.EXAMS["exam03"],
            practice_mode=True,
            practice_selection=(1, first),
        )
        with patch.object(examshell, "prepare_exercise_environment"), \
                patch.object(examshell, "clear"), \
                patch("builtins.print"):
            shell.assign_exercise(first)
            shell.attempts_by_exercise[first["name"]] = 2
            shell.assign_exercise(second)
            self.assertEqual(shell.attempts, 0)
            shell.assign_exercise(first)
            self.assertEqual(shell.attempts, 2)


class IsolatedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.rendu = examshell.BASE_DIR / "tests" / "_runtime_workspace"
        shutil.rmtree(self.rendu, ignore_errors=True)
        self.rendu.mkdir(parents=True)
        self.rendu_patch = patch.object(examshell, "RENDU_DIR", self.rendu)
        self.rendu_patch.start()

    def tearDown(self):
        self.rendu_patch.stop()
        shutil.rmtree(self.rendu, ignore_errors=True)

    def write_submission(self, exercise_name, source):
        directory = self.rendu / exercise_name
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{exercise_name}.py"
        path.write_text(source, encoding="utf-8")
        return path

    def test_valid_submission_is_graded_in_worker(self):
        self.write_submission(
            "py_bracket_validator",
            "def bracket_validator(s):\n"
            "    pairs = {')': '(', ']': '[', '}': '{'}\n"
            "    stack = []\n"
            "    for char in s:\n"
            "        if char in '([{': stack.append(char)\n"
            "        elif char in pairs:\n"
            "            if not stack or stack.pop() != pairs[char]: return False\n"
            "    return not stack\n",
        )
        passed, total, details = examshell.grade_exercise(
            "py_bracket_validator", "bracket_validator"
        )
        self.assertEqual((passed, total), (total, total), details)

    def test_bool_results_cannot_be_replaced_by_integers(self):
        self.write_submission(
            "py_bracket_validator",
            "def bracket_validator(s):\n    return 1\n",
        )
        passed, total, _ = examshell.grade_exercise(
            "py_bracket_validator", "bracket_validator"
        )
        self.assertEqual(passed, 0)
        self.assertGreater(total, 0)

    def test_top_level_infinite_loop_is_terminated(self):
        self.write_submission(
            "py_bracket_validator",
            "while True:\n    pass\n\ndef bracket_validator(s):\n    return True\n",
        )
        started = time.monotonic()
        _, error = examshell.run_submission_isolated(
            "py_bracket_validator", "bracket_validator", ("()",), timeout=0.3
        )
        self.assertIn("TIMEOUT", error)
        self.assertLess(time.monotonic() - started, 3)

    def test_cryptic_sorter_forbidden_calls_are_rejected(self):
        path = self.write_submission(
            "py_cryptic_sorter",
            "def cryptic_sorter(strings):\n    return sorted(strings)\n",
        )
        error = examshell.validate_submission_rules("py_cryptic_sorter", path)
        self.assertIn("sorted() is forbidden", error)

    def test_submission_exceptions_are_reported(self):
        self.write_submission(
            "py_bracket_validator",
            "def bracket_validator(s):\n    raise ValueError('broken solution')\n",
        )
        _, error = examshell.run_submission_isolated(
            "py_bracket_validator", "bracket_validator", ("()",)
        )
        self.assertIn("ValueError: broken solution", error)

    def test_submission_prints_do_not_corrupt_worker_protocol(self):
        self.write_submission(
            "py_bracket_validator",
            "print('module output')\n"
            "def bracket_validator(s):\n"
            "    print('function output')\n"
            "    return True\n",
        )
        result, error = examshell.run_submission_isolated(
            "py_bracket_validator", "bracket_validator", ("()",)
        )
        self.assertIsNone(error)
        self.assertIs(result, True)

    def test_invalid_function_shapes_are_rejected_without_importing(self):
        cases = {
            "missing": "def another_function(s):\n    return True\n",
            "async": "async def bracket_validator(s):\n    return True\n",
            "syntax": "def bracket_validator(s)\n    return True\n",
        }
        for label, source in cases.items():
            with self.subTest(case=label):
                self.write_submission("py_bracket_validator", source)
                error = examshell.validate_submission_file(
                    "py_bracket_validator", "bracket_validator"
                )
                self.assertIsNotNone(error)


if __name__ == "__main__":
    unittest.main()
