"""Native C grader for the Exam Rank 02 exercise catalog.

The module deliberately does not execute the bundled example solutions.  Test
expectations are defined here, and submitted code is compiled in a disposable
directory before each grading run.  This is process isolation for accidental
crashes and hangs; it is not an operating-system sandbox for hostile C code.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from exam02_catalog import C_EXERCISES


C_COMPILE_TIMEOUT_SECONDS = 20.0
C_CASE_TIMEOUT_SECONDS = 2.0
MAX_CAPTURE_BYTES = 128 * 1024
_BUILD_ROOT = Path(__file__).resolve().parent / ".c_exam_build"


@dataclass(frozen=True)
class ProgramCase:
    description: str
    argv: tuple[str, ...]
    expected_stdout: bytes


@dataclass(frozen=True)
class FunctionCase:
    description: str
    body: str
    expected: str
    expected_stdout: bytes | None = None


@dataclass(frozen=True)
class FunctionSpec:
    prelude: str
    cases: tuple[FunctionCase, ...]


@dataclass(frozen=True)
class _ProcessResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    output_limited: bool = False
    start_error: str | None = None


def _b(text: str) -> bytes:
    return text.encode("utf-8")


def _program_case(description: str, argv: Sequence[str], output: str) -> ProgramCase:
    return ProgramCase(description, tuple(argv), _b(output))


def _repeat_alpha(value: str) -> str:
    output = []
    for char in value:
        if "a" <= char <= "z":
            output.append(char * (ord(char) - ord("a") + 1))
        elif "A" <= char <= "Z":
            output.append(char * (ord(char) - ord("A") + 1))
        else:
            output.append(char)
    return "".join(output) + "\n"


def _rotate(value: str, amount: int) -> str:
    output = []
    for char in value:
        if "a" <= char <= "z":
            output.append(chr((ord(char) - ord("a") + amount) % 26 + ord("a")))
        elif "A" <= char <= "Z":
            output.append(chr((ord(char) - ord("A") + amount) % 26 + ord("A")))
        else:
            output.append(char)
    return "".join(output)


def _alpha_mirror(value: str) -> str:
    output = []
    for char in value:
        if "a" <= char <= "z":
            output.append(chr(ord("z") - (ord(char) - ord("a"))))
        elif "A" <= char <= "Z":
            output.append(chr(ord("Z") - (ord(char) - ord("A"))))
        else:
            output.append(char)
    return "".join(output)


def _prime_sum(limit: int) -> int:
    def is_prime(value: int) -> bool:
        if value < 2:
            return False
        divisor = 2
        while divisor * divisor <= value:
            if value % divisor == 0:
                return False
            divisor += 1
        return True

    return sum(value for value in range(2, limit + 1) if is_prime(value))


def _gcd(first: int, second: int) -> int:
    while second:
        first, second = second, first % second
    return first


def _factors(value: int) -> str:
    if value == 1:
        return "1"
    factors = []
    divisor = 2
    while divisor * divisor <= value:
        while value % divisor == 0:
            factors.append(str(divisor))
            value //= divisor
        divisor += 1
    if value > 1:
        factors.append(str(value))
    return "*".join(factors)


def _capitalize_first_words(value: str) -> str:
    output = []
    at_word_start = True
    for char in value:
        if char in " \t":
            output.append(char)
            at_word_start = True
        elif "A" <= char <= "Z" or "a" <= char <= "z":
            output.append(char.upper() if at_word_start else char.lower())
            at_word_start = False
        else:
            output.append(char)
            at_word_start = False
    return "".join(output)


def _capitalize_last_words(value: str) -> str:
    chars = [char.lower() if char.isascii() and char.isalpha() else char for char in value]
    for index, char in enumerate(chars):
        if char.isascii() and char.isalpha() and (
            index + 1 == len(chars) or chars[index + 1] in " \t"
        ):
            chars[index] = char.upper()
    return "".join(chars)


def _fizzbuzz() -> str:
    lines = []
    for value in range(1, 101):
        if value % 15 == 0:
            lines.append("fizzbuzz")
        elif value % 3 == 0:
            lines.append("fizz")
        elif value % 5 == 0:
            lines.append("buzz")
        else:
            lines.append(str(value))
    return "\n".join(lines) + "\n"


PROGRAM_CASES: dict[str, tuple[ProgramCase, ...]] = {
    "first_word": (
        _program_case("simple sentence", ["hello world"], "hello\n"),
        _program_case("leading spaces and tabs", ["  \talpha beta"], "alpha\n"),
        _program_case("whitespace contains no word", [" \t  \t"], "\n"),
        _program_case("empty argument", [""], "\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "fizzbuzz": (_program_case("complete sequence from 1 to 100", [], _fizzbuzz()),),
    "repeat_alpha": (
        _program_case("lowercase letters", ["abc"], _repeat_alpha("abc")),
        _program_case("mixed case and punctuation", ["Alex."], _repeat_alpha("Alex.")),
        _program_case("digits remain unchanged", ["a2C!"], _repeat_alpha("a2C!")),
        _program_case("wrong argument count", [], "\n"),
    ),
    "rev_print": (
        _program_case("ordinary text", ["dub0 a POIL"], "LIOP a 0bud\n"),
        _program_case("single character", ["z"], "z\n"),
        _program_case("empty string", [""], "\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "rot_13": (
        _program_case("alphabet wrap and case", ["Az-mN"], _rotate("Az-mN", 13) + "\n"),
        _program_case("sentence", ["My horse is Amazing."], _rotate("My horse is Amazing.", 13) + "\n"),
        _program_case("empty string", [""], "\n"),
        _program_case("wrong argument count", [], "\n"),
        _program_case("extra arguments", ["abc", "extra"], "\n"),
    ),
    "rotone": (
        _program_case("alphabet wrap and case", ["aAzZ"], "bBaA\n"),
        _program_case("nonletters", ["Hi, 42!"], _rotate("Hi, 42!", 1) + "\n"),
        _program_case("empty string", [""], "\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "search_and_replace": (
        _program_case("replace every match", ["Papache est un sabre", "a", "o"], "Popoche est un sobre\n"),
        _program_case("character absent", ["zaz", "r", "u"], "zaz\n"),
        _program_case("replacement may equal source", ["banana", "a", "a"], "banana\n"),
        _program_case("replacement arguments must be one char", ["zaz", "art", "zul"], "\n"),
        _program_case("either replacement argument may be invalid", ["zaz", "art", "u"], "\n"),
        _program_case("wrong argument count", ["abc"], "\n"),
    ),
    "ulstr": (
        _program_case("mixed case", ["L'eSPrit"], "l'EspRIT\n"),
        _program_case("digits and punctuation", ["42-Az!"], "42-aZ!\n"),
        _program_case("empty string", [""], "\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "alpha_mirror": (
        _program_case("lowercase", ["abcxyz"], _alpha_mirror("abcxyz") + "\n"),
        _program_case("mixed sentence", ["My horse!"], _alpha_mirror("My horse!") + "\n"),
        _program_case("empty string", [""], "\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "camel_to_snake": (
        _program_case("several words", ["hereIsACamelCaseWord"], "here_is_a_camel_case_word\n"),
        _program_case("two words", ["helloWorld"], "hello_world\n"),
        _program_case("already lowercase", ["plain"], "plain\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "do_op": (
        _program_case("multiplication", ["123", "*", "456"], "56088\n"),
        _program_case("signed addition", ["1", "+", "-43"], "-42\n"),
        _program_case("subtraction", ["17", "-", "29"], "-12\n"),
        _program_case("division", ["-21", "/", "4"], "-5\n"),
        _program_case("remainder", ["20", "%", "6"], "2\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "inter": (
        _program_case("duplicates removed", ["padinton", "paqefwtdjetyiytjneytjoeyjnejeyj"], "padinto\n"),
        _program_case("punctuation and case are distinct", ["aA!aba", "!Axyzab"], "aA!b\n"),
        _program_case("no intersection", ["abc", "XYZ"], "\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "last_word": (
        _program_case("ordinary words", ["FOR PONY"], "PONY\n"),
        _program_case("trailing whitespace", ["  lorem,ipsum  \t"], "lorem,ipsum\n"),
        _program_case("whitespace only", ["   \t"], "\n"),
        _program_case("wrong argument count", ["a", "b"], "\n"),
    ),
    "snake_to_camel": (
        _program_case("several words", ["here_is_a_snake_case_word"], "hereIsASnakeCaseWord\n"),
        _program_case("two words", ["hello_world"], "helloWorld\n"),
        _program_case("single word", ["plain"], "plain\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "union": (
        _program_case("ordered union", ["zpadinton", "paqefwtdjetyiytjneytjoeyjnejeyj"], "zpadintoqefwjy\n"),
        _program_case("space is a character", ["rien", "cette phrase ne cache rien"], "rienct phas\n"),
        _program_case("letter case is distinct", ["aA", "Aa"], "aA\n"),
        _program_case("empty strings", ["", ""], "\n"),
        _program_case("wrong argument count", ["one"], "\n"),
    ),
    "wdmatch": (
        _program_case("subsequence found", ["faya", "fgvvfdxcacpolhyghbreda"], "faya\n"),
        _program_case("subsequence absent", ["faya", "fgvvfdxcacpolhyghbred"], "\n"),
        _program_case("letter case is distinct", ["A", "a"], "\n"),
        _program_case("empty first string", ["", "anything"], "\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "add_prime_sum": (
        _program_case("small positive input", ["5"], f"{_prime_sum(5)}\n"),
        _program_case("larger input", ["20"], f"{_prime_sum(20)}\n"),
        _program_case("one has no primes", ["1"], "0\n"),
        _program_case("non-positive input", ["-7"], "0\n"),
        _program_case("wrong argument count", [], "0\n"),
        _program_case("extra argument", ["5", "7"], "0\n"),
    ),
    "epur_str": (
        _program_case("already normalized", ["See? It's easy"], "See? It's easy\n"),
        _program_case("mixed separators", [" \tthis   time\tworks  "], "this time works\n"),
        _program_case("empty string", [""], "\n"),
        _program_case("wrong argument count", ["a", "b"], "\n"),
    ),
    "expand_str": (
        _program_case("ordinary words", ["See? It's easy"], "See?   It's   easy\n"),
        _program_case("mixed separators", [" \tthis   time\tworks  "], "this   time   works\n"),
        _program_case("empty string", [""], "\n"),
        _program_case("wrong argument count", ["a", "b"], "\n"),
    ),
    "hidenp": (
        _program_case("hidden subsequence", ["abc", "2altrb53c.sse"], "1\n"),
        _program_case("wrong order", ["abc", "btarc"], "0\n"),
        _program_case("letter case is distinct", ["A", "a"], "0\n"),
        _program_case("empty string is hidden", ["", "anything"], "1\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "paramsum": (
        _program_case("no arguments", [], "0\n"),
        _program_case("one argument", ["anything"], "1\n"),
        _program_case("several arguments", ["1", "2", "3", "5"], "4\n"),
    ),
    "pgcd": (
        _program_case("shared factor", ["42", "12"], f"{_gcd(42, 12)}\n"),
        _program_case("coprime values", ["17", "3"], "1\n"),
        _program_case("equal values", ["81", "81"], "81\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "print_hex": (
        _program_case("zero", ["0"], "0\n"),
        _program_case("single hex digit", ["10"], "a\n"),
        _program_case("multiple digits", ["5156454"], "4eae66\n"),
        _program_case("wrong argument count", [], "\n"),
    ),
    "rstr_capitalizer": (
        _program_case("one sentence", ["a FiRSt LiTTlE TESt"], _capitalize_last_words("a FiRSt LiTTlE TESt") + "\n"),
        _program_case("spacing retained", ["  HELLO\tWoRLD  "], _capitalize_last_words("  HELLO\tWoRLD  ") + "\n"),
        _program_case("punctuation does not end a word", ["But... WOW!"], "but... wow!\n"),
        _program_case("several arguments", ["ONE two", "x Y"], _capitalize_last_words("ONE two") + "\n" + _capitalize_last_words("x Y") + "\n"),
        _program_case("no arguments", [], "\n"),
    ),
    "str_capitalizer": (
        _program_case("one sentence", ["a FiRSt LiTTlE TESt"], _capitalize_first_words("a FiRSt LiTTlE TESt") + "\n"),
        _program_case("punctuation stays in word", ["__SecONd teST"], _capitalize_first_words("__SecONd teST") + "\n"),
        _program_case("several arguments", ["ONE two", "x Y"], _capitalize_first_words("ONE two") + "\n" + _capitalize_first_words("x Y") + "\n"),
        _program_case("no arguments", [], "\n"),
    ),
    "tab_mult": (
        _program_case("small table", ["3"], "".join(f"{i} x 3 = {i * 3}\n" for i in range(1, 10))),
        _program_case("two digit value", ["19"], "".join(f"{i} x 19 = {i * 19}\n" for i in range(1, 10))),
        _program_case("wrong argument count", [], "\n"),
    ),
    "fprime": (
        _program_case("composite number", ["225225"], _factors(225225) + "\n"),
        _program_case("prime number", ["9539"], "9539\n"),
        _program_case("one", ["1"], "1\n"),
        _program_case("repeated factor two", ["64"], "2*2*2*2*2*2\n"),
        _program_case("small composite", ["42"], "2*3*7\n"),
        _program_case("wrong argument count", [], "\n"),
        _program_case("extra argument", ["42", "21"], "\n"),
    ),
    "rev_wstr": (
        _program_case("several words", ["Wingardium Leviosa"], "Leviosa Wingardium\n"),
        _program_case("single word", ["abcdefghijklm"], "abcdefghijklm\n"),
        _program_case("longer sentence", ["You hate people!"], "people! hate You\n"),
        _program_case("wrong argument count", [], "\n"),
        _program_case("extra argument", ["one two", "extra"], "\n"),
    ),
    "rostring": (
        _program_case("several words and extra spaces", ["Que la      lumiere soit"], "la lumiere soit Que\n"),
        _program_case("leading whitespace", ["  AkjhZ zLKIJz , 23y"], "zLKIJz , 23y AkjhZ\n"),
        _program_case("tabs delimit words", ["\tfirst\tsecond  third\t"], "second third first\n"),
        _program_case("single word", ["abc   "], "abc\n"),
        _program_case("extra arguments ignored by subject", ["first", "2", "3"], "first\n"),
        _program_case("no arguments", [], "\n"),
    ),
}


def _function_case(description: str, body: str, expected: str) -> FunctionCase:
    return FunctionCase(description, body.strip(), expected)


def _output_case(description: str, body: str, expected_stdout: str) -> FunctionCase:
    return FunctionCase(description, body.strip(), repr(expected_stdout), _b(expected_stdout))


FUNCTION_SPECS: dict[str, FunctionSpec] = {
    "ft_putstr": FunctionSpec(
        "void ft_putstr(char *str);",
        (
            _output_case("ordinary string", 'char value[] = "hello"; ft_putstr(value); return 0;', "hello"),
            _output_case("empty string", 'char value[] = ""; ft_putstr(value); return 0;', ""),
            _output_case("spaces and punctuation", 'char value[] = "42 C!"; ft_putstr(value); return 0;', "42 C!"),
        ),
    ),
    "ft_strcpy": FunctionSpec(
        "char *ft_strcpy(char *s1, char *s2);",
        (
            _function_case(
                "ordinary string",
                'char source[] = "hello"; char dest[32] = "xxxxxxxx"; '
                'char *result = ft_strcpy(dest, source); '
                'return !(result == dest && strcmp(dest, "hello") == 0);',
                'destination and return pointer equal "hello"',
            ),
            _function_case(
                "empty source",
                'char source[] = ""; char dest[8] = "abc"; '
                'char *result = ft_strcpy(dest, source); '
                'return !(result == dest && dest[0] == \'\\0\');',
                "empty destination and original destination pointer",
            ),
            _function_case(
                "spaces and punctuation",
                'char source[] = "a b!"; char dest[16] = ""; '
                'char *result = ft_strcpy(dest, source); '
                'return !(result == dest && strcmp(dest, source) == 0);',
                "exact copied string and original destination pointer",
            ),
        ),
    ),
    "ft_strlen": FunctionSpec(
        "int ft_strlen(char *str);",
        tuple(
            _function_case(desc, f'char value[] = "{literal}"; return ft_strlen(value) != {length};', str(length))
            for desc, literal, length in (
                ("empty string", "", 0),
                ("single character", "x", 1),
                ("ordinary string", "hello", 5),
                ("spaces count as characters", "a b c", 5),
            )
        ),
    ),
    "ft_swap": FunctionSpec(
        "void ft_swap(int *a, int *b);",
        (
            _function_case("positive values", "int a = 4, b = 9; ft_swap(&a, &b); return !(a == 9 && b == 4);", "a=9, b=4"),
            _function_case("negative and zero", "int a = -7, b = 0; ft_swap(&a, &b); return !(a == 0 && b == -7);", "a=0, b=-7"),
            _function_case("equal values", "int a = 5, b = 5; ft_swap(&a, &b); return !(a == 5 && b == 5);", "a=5, b=5"),
        ),
    ),
    "ft_atoi": FunctionSpec(
        "int ft_atoi(const char *str);",
        (
            _function_case("zero", 'return ft_atoi("0") != 0;', "0"),
            _function_case("leading whitespace and sign", 'return ft_atoi(" \\t\\n-42xyz") != -42;', "-42"),
            _function_case("all standard leading whitespace", 'return ft_atoi("\\v\\f\\r\\t\\n 17") != 17;', "17"),
            _function_case("explicit plus", 'return ft_atoi("+123") != 123;', "123"),
            _function_case("no leading digits", 'return ft_atoi("words42") != 0;', "0"),
            _function_case("multiple signs are invalid", 'return ft_atoi("--12") != 0;', "0"),
        ),
    ),
    "ft_strcmp": FunctionSpec(
        "int ft_strcmp(char *s1, char *s2);",
        (
            _function_case("equal strings", 'char a[]="same", b[]="same"; return ft_strcmp(a,b) != 0;', "zero"),
            _function_case("first is smaller", 'char a[]="abc", b[]="abd"; return ft_strcmp(a,b) >= 0;', "negative value"),
            _function_case("prefix is smaller", 'char a[]="ab", b[]="abc"; return ft_strcmp(a,b) >= 0;', "negative value"),
            _function_case("unsigned character ordering", 'char a[]={ (char)255, 0 }, b[]={ 1, 0 }; return ft_strcmp(a,b) <= 0;', "positive value"),
        ),
    ),
    "ft_strcspn": FunctionSpec(
        "size_t ft_strcspn(const char *s, const char *reject);",
        (
            _function_case("reject in middle", 'return ft_strcspn("hello", "xyzl") != (size_t)2;', "2"),
            _function_case("no rejected characters", 'return ft_strcspn("hello", "XYZ") != (size_t)5;', "5"),
            _function_case("first character rejected", 'return ft_strcspn("abc", "a") != (size_t)0;', "0"),
            _function_case("empty source", 'return ft_strcspn("", "abc") != (size_t)0;', "0"),
            _function_case("empty reject set", 'return ft_strcspn("abc", "") != (size_t)3;', "3"),
        ),
    ),
    "ft_strdup": FunctionSpec(
        "char *ft_strdup(char *src);",
        (
            _function_case(
                "ordinary string",
                'char source[]="duplicate me"; char *got=ft_strdup(source); '
                'int bad=(got==NULL || got==source || strcmp(got,source)!=0); free(got); return bad;',
                "a distinct allocation containing duplicate me",
            ),
            _function_case(
                "empty string",
                'char source[]=""; char *got=ft_strdup(source); '
                'int bad=(got==NULL || got==source || strcmp(got,"")!=0); free(got); return bad;',
                "a distinct allocated empty string",
            ),
            _function_case(
                "punctuation",
                'char source[]="a b! 42"; char *got=ft_strdup(source); '
                'int bad=(got==NULL || strcmp(got,source)!=0); '
                'if (got != NULL) got[0]=\'A\'; '
                'bad = bad || source[0] != \'a\'; free(got); return bad;',
                "independent exact copy",
            ),
        ),
    ),
    "ft_strpbrk": FunctionSpec(
        "char *ft_strpbrk(const char *s1, const char *s2);",
        (
            _function_case("match in middle", 'const char *s="hello"; return ft_strpbrk(s,"xyzl") != s + 2;', "pointer to index 2"),
            _function_case("earliest source match wins", 'const char *s="cab"; return ft_strpbrk(s,"ba") != s + 1;', "pointer to index 1"),
            _function_case("no match", 'return ft_strpbrk("hello","XYZ") != NULL;', "NULL"),
            _function_case("empty needle set", 'return ft_strpbrk("hello","") != NULL;', "NULL"),
            _function_case("empty source", 'return ft_strpbrk("","abc") != NULL;', "NULL"),
        ),
    ),
    "ft_strrev": FunctionSpec(
        "char *ft_strrev(char *str);",
        (
            _function_case("ordinary string", 'char s[]="abcdef"; char *got=ft_strrev(s); return !(got==s && strcmp(s,"fedcba")==0);', 'same pointer containing "fedcba"'),
            _function_case("odd length", 'char s[]="abcde"; char *got=ft_strrev(s); return !(got==s && strcmp(s,"edcba")==0);', 'same pointer containing "edcba"'),
            _function_case("single character", 'char s[]="x"; char *got=ft_strrev(s); return !(got==s && strcmp(s,"x")==0);', 'same pointer containing "x"'),
            _function_case("empty string", 'char s[]=""; char *got=ft_strrev(s); return !(got==s && strcmp(s,"")==0);', "same empty-string pointer"),
        ),
    ),
    "ft_strspn": FunctionSpec(
        "size_t ft_strspn(const char *s, const char *accept);",
        (
            _function_case("accepted prefix", 'return ft_strspn("abcde123","edcba") != (size_t)5;', "5"),
            _function_case("first character rejected", 'return ft_strspn("hello","xyz") != (size_t)0;', "0"),
            _function_case("whole string accepted", 'return ft_strspn("aabbcc","abc") != (size_t)6;', "6"),
            _function_case("empty source", 'return ft_strspn("","abc") != (size_t)0;', "0"),
            _function_case("empty accept set", 'return ft_strspn("abc","") != (size_t)0;', "0"),
        ),
    ),
    "is_power_of_2": FunctionSpec(
        "int is_power_of_2(unsigned int n);",
        tuple(
            _function_case(desc, f"return is_power_of_2({value}u) != {expected};", str(expected))
            for desc, value, expected in (
                ("zero", 0, 0),
                ("one", 1, 1),
                ("small power", 2, 1),
                ("non-power", 3, 0),
                ("large power", 1073741824, 1),
            )
        ),
    ),
    "max": FunctionSpec(
        "int max(int *tab, unsigned int len);",
        (
            _function_case("mixed values", "int values[]={-4,9,2,9,1}; return max(values,5u)!=9;", "9"),
            _function_case("all negative", "int values[]={-8,-2,-30}; return max(values,3u)!=-2;", "-2"),
            _function_case("single value", "int values[]={42}; return max(values,1u)!=42;", "42"),
            _function_case("empty array", "return max(NULL,0u)!=0;", "0"),
        ),
    ),
    "print_bits": FunctionSpec(
        "void print_bits(unsigned char octet);",
        (
            _output_case("zero byte", "print_bits((unsigned char)0); return 0;", "00000000"),
            _output_case("value two", "print_bits((unsigned char)2); return 0;", "00000010"),
            _output_case("alternating bits", "print_bits((unsigned char)170); return 0;", "10101010"),
            _output_case("all bits set", "print_bits((unsigned char)255); return 0;", "11111111"),
        ),
    ),
    "reverse_bits": FunctionSpec(
        "unsigned char reverse_bits(unsigned char octet);",
        tuple(
            _function_case(desc, f"return reverse_bits((unsigned char){value}) != (unsigned char){expected};", hex(expected))
            for desc, value, expected in (
                ("zero", 0, 0),
                ("single low bit", 1, 128),
                ("subject-style value", 0x41, 0x82),
                ("asymmetric pattern", 0x16, 0x68),
                ("all bits set", 255, 255),
            )
        ),
    ),
    "swap_bits": FunctionSpec(
        "unsigned char swap_bits(unsigned char octet);",
        tuple(
            _function_case(desc, f"return swap_bits((unsigned char){value}) != (unsigned char){expected};", hex(expected))
            for desc, value, expected in (
                ("zero", 0x00, 0x00),
                ("subject-style value", 0x41, 0x14),
                ("unequal nibbles", 0xAB, 0xBA),
                ("equal nibbles", 0x77, 0x77),
                ("all bits set", 0xFF, 0xFF),
            )
        ),
    ),
    "ft_atoi_base": FunctionSpec(
        "int ft_atoi_base(const char *str, int str_base);",
        (
            _function_case("binary", 'return ft_atoi_base("101101",2)!=45;', "45"),
            _function_case("uppercase hexadecimal", 'return ft_atoi_base("12FDB3",16)!=1244595;', "1244595"),
            _function_case("negative hexadecimal", 'return ft_atoi_base("-2a",16)!=-42;', "-42"),
            _function_case("base eight", 'return ft_atoi_base("755",8)!=493;', "493"),
            _function_case("plus sign is not recognized", 'return ft_atoi_base("+2a",16)!=0;', "0"),
            _function_case("digit equal to base is invalid", 'return ft_atoi_base("2",2)!=0;', "0"),
        ),
    ),
    "ft_list_size": FunctionSpec(
        '#include "ft_list.h"\nint ft_list_size(t_list *begin_list);',
        (
            _function_case("empty list", "return ft_list_size(NULL)!=0;", "0"),
            _function_case("single node", "int value=1; t_list a={NULL,&value}; return ft_list_size(&a)!=1;", "1"),
            _function_case("several nodes", "int a_data=1,b_data=2,c_data=3; t_list c={NULL,&c_data}; t_list b={&c,&b_data}; t_list a={&b,&a_data}; return ft_list_size(&a)!=3;", "3"),
            _function_case("longer list", "int d[5]={0}; t_list n4={NULL,&d[4]},n3={&n4,&d[3]},n2={&n3,&d[2]},n1={&n2,&d[1]},n0={&n1,&d[0]}; return ft_list_size(&n0)!=5;", "5"),
        ),
    ),
    "ft_range": FunctionSpec(
        "int *ft_range(int start, int end);",
        (
            _function_case("ascending", "int exp[]={1,2,3}; int *got=ft_range(1,3); int bad=(got==NULL || memcmp(got,exp,sizeof(exp))!=0); free(got); return bad;", "[1, 2, 3]"),
            _function_case("crosses zero", "int exp[]={-1,0,1,2}; int *got=ft_range(-1,2); int bad=(got==NULL || memcmp(got,exp,sizeof(exp))!=0); free(got); return bad;", "[-1, 0, 1, 2]"),
            _function_case("single value", "int *got=ft_range(0,0); int bad=(got==NULL || got[0]!=0); free(got); return bad;", "[0]"),
            _function_case("descending", "int exp[]={3,2,1,0,-1}; int *got=ft_range(3,-1); int bad=(got==NULL || memcmp(got,exp,sizeof(exp))!=0); free(got); return bad;", "[3, 2, 1, 0, -1]"),
        ),
    ),
    "ft_rrange": FunctionSpec(
        "int *ft_rrange(int start, int end);",
        (
            _function_case("start below end", "int exp[]={3,2,1}; int *got=ft_rrange(1,3); int bad=(got==NULL || memcmp(got,exp,sizeof(exp))!=0); free(got); return bad;", "[3, 2, 1]"),
            _function_case("crosses zero", "int exp[]={2,1,0,-1}; int *got=ft_rrange(-1,2); int bad=(got==NULL || memcmp(got,exp,sizeof(exp))!=0); free(got); return bad;", "[2, 1, 0, -1]"),
            _function_case("single value", "int *got=ft_rrange(0,0); int bad=(got==NULL || got[0]!=0); free(got); return bad;", "[0]"),
            _function_case("start above end", "int exp[]={-3,-2,-1,0}; int *got=ft_rrange(0,-3); int bad=(got==NULL || memcmp(got,exp,sizeof(exp))!=0); free(got); return bad;", "[-3, -2, -1, 0]"),
        ),
    ),
    "lcm": FunctionSpec(
        "unsigned int lcm(unsigned int a, unsigned int b);",
        tuple(
            _function_case(desc, f"return lcm({a}u,{b}u)!={expected}u;", str(expected))
            for desc, a, b, expected in (
                ("both zero", 0, 0, 0),
                ("first operand zero", 0, 9, 0),
                ("second operand zero", 9, 0, 0),
                ("coprime", 7, 5, 35),
                ("common factors", 12, 18, 36),
                ("equal values", 42, 42, 42),
            )
        ),
    ),
    "flood_fill": FunctionSpec(
        """typedef struct s_point { int x; int y; } t_point;
void flood_fill(char **tab, t_point size, t_point begin);""",
        (
            _function_case(
                "subject example zone",
                """char r0[]="11111111", r1[]="10001001", r2[]="10010001", r3[]="10110001", r4[]="11100001";
char *area[]={r0,r1,r2,r3,r4}; const char *expected[]={"FFFFFFFF","F000F00F","F00F000F","F0FF000F","FFF0000F"};
t_point size={8,5}, begin={7,4}; int i; flood_fill(area,size,begin);
for(i=0;i<5;i++) { if(strcmp(area[i],expected[i])!=0) return 1; } return 0;""",
                "the connected '1' zone replaced with F",
            ),
            _function_case(
                "single cell",
                """char r0[]="a"; char *area[]={r0}; t_point size={1,1}, begin={0,0};
flood_fill(area,size,begin); return strcmp(area[0],"F")!=0;""",
                '"F"',
            ),
            _function_case(
                "diagonal cells are not connected",
                """char r0[]="aba", r1[]="bab", r2[]="aba"; char *area[]={r0,r1,r2};
const char *expected[]={"Fba","bab","aba"}; t_point size={3,3}, begin={0,0}; int i;
flood_fill(area,size,begin); for(i=0;i<3;i++) { if(strcmp(area[i],expected[i])!=0) return 1; } return 0;""",
                "only the starting cell filled",
            ),
            _function_case(
                "bounded interior region",
                """char r0[]="xxxxx", r1[]="xaaax", r2[]="xaxax", r3[]="xaaax", r4[]="xxxxx"; char *area[]={r0,r1,r2,r3,r4};
const char *expected[]={"xxxxx","xFFFx","xFxFx","xFFFx","xxxxx"}; t_point size={5,5}, begin={1,1}; int i;
flood_fill(area,size,begin); for(i=0;i<5;i++) { if(strcmp(area[i],expected[i])!=0) return 1; } return 0;""",
                "only the connected interior region filled",
            ),
            _function_case(
                "zone already contains F",
                """char r0[]="FFF", r1[]="FaF", r2[]="FFF"; char *area[]={r0,r1,r2};
const char *expected[]={"FFF","FaF","FFF"}; t_point size={3,3}, begin={0,0}; int i;
flood_fill(area,size,begin); for(i=0;i<3;i++) { if(strcmp(area[i],expected[i])!=0) return 1; } return 0;""",
                "unchanged connected F zone and termination",
            ),
        ),
    ),
    "ft_itoa": FunctionSpec(
        "char *ft_itoa(int nbr);",
        tuple(
            _function_case(
                desc,
                f"char *got=ft_itoa({value}); int bad=(got==NULL || strcmp(got,\"{expected}\")!=0); free(got); return bad;",
                repr(expected),
            )
            for desc, value, expected in (
                ("zero", 0, "0"),
                ("positive number", 123456, "123456"),
                ("negative number", -42, "-42"),
                ("maximum int", 2147483647, "2147483647"),
                ("minimum int", "(-2147483647 - 1)", "-2147483648"),
            )
        ),
    ),
    "ft_list_foreach": FunctionSpec(
        """#include "ft_list.h"
void ft_list_foreach(t_list *begin_list, void (*f)(void *));
static void add_ten(void *data) { *(int *)data += 10; }
static void negate(void *data) { *(int *)data = -*(int *)data; }""",
        (
            _function_case("empty list", "ft_list_foreach(NULL,add_ten); return 0;", "no callback and no crash"),
            _function_case("single node", "int value=2; t_list node={NULL,&value}; ft_list_foreach(&node,add_ten); return value!=12;", "12"),
            _function_case("every node visited", "int a=1,b=-2,c=3; t_list nc={NULL,&c},nb={&nc,&b},na={&nb,&a}; ft_list_foreach(&na,add_ten); return !(a==11 && b==8 && c==13);", "[11, 8, 13]"),
            _function_case("callback order-compatible mutation", "int a=1,b=0,c=-4; t_list nc={NULL,&c},nb={&nc,&b},na={&nb,&a}; ft_list_foreach(&na,negate); return !(a==-1 && b==0 && c==4);", "[-1, 0, 4]"),
        ),
    ),
    "ft_list_remove_if": FunctionSpec(
        """#include "ft_list.h"
void ft_list_remove_if(t_list **begin_list, void *data_ref, int (*cmp)());
static int value_cmp(void *left, void *right) { return strcmp((const char *)left,(const char *)right); }
static t_list *new_node(void *data) { t_list *node=(t_list *)malloc(sizeof(*node)); if(node!=NULL){node->data=data;node->next=NULL;} return node; }
static void release_nodes(t_list *node) { while(node!=NULL){t_list *next=node->next;free(node);node=next;} }
static int matches(t_list *node, const char *const *values, size_t count) { size_t i=0; while(node!=NULL && i<count){if(strcmp((const char *)node->data,values[i])!=0)return 0;node=node->next;i++;}return node==NULL && i==count; }""",
        (
            _function_case("empty list", 't_list *head=NULL; ft_list_remove_if(&head,(void *)"x",value_cmp); return head!=NULL;', "empty list"),
            _function_case(
                "remove head",
                't_list *a=new_node((void *)"x"), *b=new_node((void *)"keep"); const char *expected[]={"keep"}; '
                'if(a==NULL||b==NULL){release_nodes(a);release_nodes(b);return 1;} a->next=b; '
                'ft_list_remove_if(&a,(void *)"x",value_cmp); {int bad=!matches(a,expected,1);release_nodes(a);return bad;}',
                '["keep"]',
            ),
            _function_case(
                "remove consecutive and trailing matches",
                't_list *a=new_node((void *)"x"),*b=new_node((void *)"x"),*c=new_node((void *)"a"),*d=new_node((void *)"x"); const char *expected[]={"a"}; '
                'if(!a||!b||!c||!d){release_nodes(a);release_nodes(b);release_nodes(c);release_nodes(d);return 1;} a->next=b;b->next=c;c->next=d; '
                'ft_list_remove_if(&a,(void *)"x",value_cmp); {int bad=!matches(a,expected,1);release_nodes(a);return bad;}',
                '["a"]',
            ),
            _function_case(
                "leave nonmatching list intact",
                't_list *a=new_node((void *)"a"),*b=new_node((void *)"b"),*c=new_node((void *)"c"); const char *expected[]={"a","b","c"}; '
                'if(!a||!b||!c){release_nodes(a);release_nodes(b);release_nodes(c);return 1;} a->next=b;b->next=c; '
                'ft_list_remove_if(&a,(void *)"x",value_cmp); {int bad=!matches(a,expected,3);release_nodes(a);return bad;}',
                '["a", "b", "c"]',
            ),
            _function_case(
                "compare equal data stored at distinct addresses",
                'char value[]="same", reference[]="same"; t_list *head=new_node(value); int bad; '
                'if(head==NULL)return 1; ft_list_remove_if(&head,reference,value_cmp); '
                'bad=(head!=NULL); release_nodes(head); return bad;',
                "empty list",
            ),
        ),
    ),
    "ft_split": FunctionSpec(
        """char **ft_split(char *str);
static int split_matches(char **got, const char *const *expected, size_t count) { size_t i; if(got==NULL)return 0; for(i=0;i<count;i++){if(got[i]==NULL || strcmp(got[i],expected[i])!=0)return 0;} return got[count]==NULL; }
static void release_split(char **got, size_t count) { size_t i; if(got==NULL)return; for(i=0;i<count && got[i]!=NULL;i++)free(got[i]);free(got); }""",
        (
            _function_case(
                "ordinary sentence",
                'char input[]="hello world from C"; const char *expected[]={"hello","world","from","C"}; char **got=ft_split(input); int bad=!split_matches(got,expected,4); release_split(got,4); return bad;',
                '["hello", "world", "from", "C"]',
            ),
            _function_case(
                "mixed whitespace",
                'char input[]=" \\tone\\n two  \\tthree\\n"; const char *expected[]={"one","two","three"}; char **got=ft_split(input); int bad=!split_matches(got,expected,3); release_split(got,3); return bad;',
                '["one", "two", "three"]',
            ),
            _function_case(
                "single word",
                'char input[]="single"; const char *expected[]={"single"}; char **got=ft_split(input); int bad=!split_matches(got,expected,1); release_split(got,1); return bad;',
                '["single"]',
            ),
            _function_case(
                "empty string",
                'char input[]=""; char **got=ft_split(input); int bad=(got==NULL || got[0]!=NULL); release_split(got,0); return bad;',
                "allocated array containing only NULL",
            ),
            _function_case(
                "whitespace only",
                'char input[]=" \\t\\n "; char **got=ft_split(input); int bad=(got==NULL || got[0]!=NULL); release_split(got,0); return bad;',
                "allocated array containing only NULL",
            ),
        ),
    ),
    "sort_int_tab": FunctionSpec(
        "void sort_int_tab(int *tab, unsigned int size);",
        (
            _function_case("mixed values", "int got[]={4,-1,9,2,0},expected[]={-1,0,2,4,9}; sort_int_tab(got,5u); return memcmp(got,expected,sizeof(got))!=0;", "[-1, 0, 2, 4, 9]"),
            _function_case("duplicates retained", "int got[]={3,1,3,2,1},expected[]={1,1,2,3,3}; sort_int_tab(got,5u); return memcmp(got,expected,sizeof(got))!=0;", "[1, 1, 2, 3, 3]"),
            _function_case("already sorted", "int got[]={-2,0,7},expected[]={-2,0,7}; sort_int_tab(got,3u); return memcmp(got,expected,sizeof(got))!=0;", "[-2, 0, 7]"),
            _function_case("single element", "int got[]={42}; sort_int_tab(got,1u); return got[0]!=42;", "[42]"),
            _function_case("zero elements", "int dummy=7; sort_int_tab(&dummy,0u); return dummy!=7;", "unchanged storage"),
        ),
    ),
    "sort_list": FunctionSpec(
        """#include "list.h"
t_list *sort_list(t_list *lst, int (*cmp)(int, int));
static int ascending(int a,int b){return a<=b;}
static int descending(int a,int b){return a>=b;}
static int list_values(t_list *node,const int *expected,size_t count){size_t i=0;while(node!=NULL && i<count){if(node->data!=expected[i])return 0;node=node->next;i++;}return node==NULL && i==count;}""",
        (
            _function_case("ascending mixed list", "t_list c={2,NULL},b={-1,&c},a={4,&b}; int expected[]={-1,2,4}; t_list *got=sort_list(&a,ascending); return !list_values(got,expected,3);", "[-1, 2, 4]"),
            _function_case("descending order", "t_list d={2,NULL},c={9,&d},b={-1,&c},a={4,&b}; int expected[]={9,4,2,-1}; t_list *got=sort_list(&a,descending); return !list_values(got,expected,4);", "[9, 4, 2, -1]"),
            _function_case("duplicates retained", "t_list d={1,NULL},c={3,&d},b={1,&c},a={3,&b}; int expected[]={1,1,3,3}; t_list *got=sort_list(&a,ascending); return !list_values(got,expected,4);", "[1, 1, 3, 3]"),
            _function_case("single node", "t_list a={42,NULL}; int expected[]={42}; t_list *got=sort_list(&a,ascending); return !list_values(got,expected,1);", "[42]"),
            _function_case("empty list", "return sort_list(NULL,ascending)!=NULL;", "NULL"),
        ),
    ),
}


_WILDCARD_SOURCE_EXERCISES = {"do_op", "flood_fill"}
_REQUIRED_SUBMITTED_HEADERS: dict[str, tuple[str, ...]] = {
    "ft_list_size": ("ft_list.h",),
    "ft_list_foreach": ("ft_list.h",),
}
_SUPPLIED_HEADERS: dict[str, dict[str, str]] = {
    "sort_list": {
        "list.h": """#ifndef EXAMSHELL_LIST_H
# define EXAMSHELL_LIST_H
typedef struct s_list t_list;
struct s_list
{
    int data;
    t_list *next;
};
#endif
""",
    },
    "ft_list_remove_if": {
        "ft_list.h": """#ifndef EXAMSHELL_FT_LIST_H
# define EXAMSHELL_FT_LIST_H
typedef struct s_list
{
    struct s_list *next;
    void *data;
} t_list;
#endif
""",
    },
}


def _normalize_stdout(payload: bytes) -> bytes:
    """Normalize only platform newline translation, preserving other bytes."""
    return payload.replace(b"\r\n", b"\n")


def _display_bytes(payload: bytes, limit: int = 400) -> str:
    clipped = payload[:limit]
    text = clipped.decode("utf-8", errors="replace")
    suffix = "... <truncated>" if len(payload) > limit else ""
    return repr(text + suffix)


def _creation_flags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _quote_windows_argument(argument: str) -> str:
    """Quote one argv item while preserving it exactly under MSVCRT rules.

    Python's default Windows list conversion leaves a bare ``*`` unquoted.
    Quoting every item preserves empty strings and handles trailing
    backslashes/embedded quotes.  MinGW's additional wildcard layer is
    disabled separately at link time for submitted programs.
    """
    result = ['"']
    backslashes = 0
    for char in argument:
        if char == "\\":
            backslashes += 1
        elif char == '"':
            result.append("\\" * (backslashes * 2 + 1))
            result.append('"')
            backslashes = 0
        else:
            if backslashes:
                result.append("\\" * backslashes)
                backslashes = 0
            result.append(char)
    if backslashes:
        result.append("\\" * (backslashes * 2))
    result.append('"')
    return "".join(result)


def _run_process(command: Sequence[str], cwd: Path, timeout: float) -> _ProcessResult:
    """Run a child with concurrent, bounded stdout/stderr collection."""
    command_parts = [str(part) for part in command]
    process_command: Sequence[str] | str
    if os.name == "nt":
        process_command = " ".join(
            _quote_windows_argument(part) for part in command_parts
        )
    else:
        process_command = command_parts
    try:
        process = subprocess.Popen(
            process_command,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=_creation_flags(),
        )
    except OSError as error:
        return _ProcessResult(None, b"", b"", start_error=str(error))

    stdout = bytearray()
    stderr = bytearray()
    output_limited = threading.Event()

    def drain(stream, destination: bytearray) -> None:
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                room = MAX_CAPTURE_BYTES - len(destination)
                if room > 0:
                    destination.extend(chunk[:room])
                if len(chunk) > room:
                    output_limited.set()
                    try:
                        process.kill()
                    except OSError:
                        pass
                    break
        except (OSError, ValueError):
            pass

    stdout_thread = threading.Thread(target=drain, args=(process.stdout, stdout), daemon=True)
    stderr_thread = threading.Thread(target=drain, args=(process.stderr, stderr), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    timed_out = False
    try:
        process.wait(timeout=max(0.01, timeout))
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            pass

    # A killed process closes its pipe handles once wait() completes.  Closing
    # here also prevents a malicious descendant from keeping a reader blocked.
    if process.poll() is not None:
        stdout_thread.join(timeout=1.0)
        stderr_thread.join(timeout=1.0)
    for stream in (process.stdout, process.stderr):
        try:
            stream.close()
        except (OSError, ValueError):
            pass
    stdout_thread.join(timeout=0.2)
    stderr_thread.join(timeout=0.2)

    return _ProcessResult(
        process.returncode,
        bytes(stdout),
        bytes(stderr),
        timed_out=timed_out,
        output_limited=output_limited.is_set(),
    )


def _find_compiler() -> str | None:
    # ``cc`` is the documented interface.  The fallbacks make Unix test
    # environments usable without weakening the MinGW path on Windows.
    return shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


def _exercise_directory(exercise_name: str, rendu_dir: str | os.PathLike[str]) -> Path:
    return Path(rendu_dir).resolve() / exercise_name


def _submission_files(
    exercise_name: str, rendu_dir: str | os.PathLike[str]
) -> tuple[list[Path], list[Path]]:
    exercise_dir = _exercise_directory(exercise_name, rendu_dir)
    if exercise_name in _WILDCARD_SOURCE_EXERCISES:
        sources = sorted(exercise_dir.glob("*.c"), key=lambda path: path.name.lower())
        headers = sorted(exercise_dir.glob("*.h"), key=lambda path: path.name.lower())
    else:
        sources = [exercise_dir / f"{exercise_name}.c"]
        headers = [exercise_dir / name for name in _REQUIRED_SUBMITTED_HEADERS.get(exercise_name, ())]
    return sources, headers


def validate_c_submission(
    exercise_name: str, rendu_dir: str | os.PathLike[str]
) -> str | None:
    """Validate the submitted C file layout without executing student code."""
    metadata = C_EXERCISES.get(exercise_name)
    if metadata is None:
        return f"Unknown C exercise: {exercise_name}"

    exercise_dir = _exercise_directory(exercise_name, rendu_dir)
    if not exercise_dir.is_dir():
        return (
            "Submission directory not found:\n"
            f"  {exercise_dir}\n\n"
            f"Create rendu/{exercise_name}/ and place the required C files there."
        )

    sources, headers = _submission_files(exercise_name, rendu_dir)
    if exercise_name in _WILDCARD_SOURCE_EXERCISES:
        if not sources:
            return f"No C source files found in:\n  {exercise_dir}\n\nSubmit at least one top-level .c file."
    else:
        expected = sources[0]
        if not expected.is_file():
            return (
                "File not found:\n"
                f"  {expected}\n\n"
                f"Expected: rendu/{exercise_name}/{exercise_name}.c"
            )

    for header in headers:
        if not header.is_file():
            return (
                "Required header not found:\n"
                f"  {header}\n\n"
                f"The subject requires {header.name} to be submitted with the source."
            )

    expected_parent = exercise_dir.resolve()
    for path in [*sources, *headers]:
        try:
            resolved = path.resolve(strict=True)
        except OSError as error:
            return f"Could not access submitted file {path.name}: {error}"
        if not resolved.is_file() or resolved.parent != expected_parent:
            return f"Submitted files must be regular top-level files: {path.name}"
        try:
            if resolved.stat().st_size > 2 * 1024 * 1024:
                return f"Submitted file is too large (2 MiB maximum): {path.name}"
        except OSError as error:
            return f"Could not inspect submitted file {path.name}: {error}"
    return None


def validate_c_specs() -> list[str]:
    """Return structural errors in the C catalog and native test definitions."""
    errors: list[str] = []
    catalog_names = set(C_EXERCISES)
    test_names = set(PROGRAM_CASES) | set(FUNCTION_SPECS)
    if len(catalog_names) != 57:
        errors.append(f"C catalog has {len(catalog_names)} exercises; expected 57")
    for name in sorted(catalog_names - test_names):
        errors.append(f"{name}: no native C tests configured")
    for name in sorted(test_names - catalog_names):
        errors.append(f"orphan native C test group: {name}")
    for name in sorted(catalog_names):
        metadata = C_EXERCISES[name]
        kind = metadata.get("kind")
        if kind == "program":
            cases = PROGRAM_CASES.get(name, ())
            if name in FUNCTION_SPECS:
                errors.append(f"{name}: program also has a function harness")
            minimum = 1 if name == "fizzbuzz" else 3
            maximum = 7 if name == "fprime" else 6
            if not minimum <= len(cases) <= maximum:
                errors.append(
                    f"{name}: expected {minimum}-{maximum} program cases, "
                    f"found {len(cases)}"
                )
            for case in cases:
                if not isinstance(case, ProgramCase) or not case.description:
                    errors.append(f"{name}: malformed program case")
                    break
        elif kind == "function":
            spec = FUNCTION_SPECS.get(name)
            if name in PROGRAM_CASES:
                errors.append(f"{name}: function also has program cases")
            if spec is None:
                continue
            if not spec.prelude.strip() or not 3 <= len(spec.cases) <= 6:
                errors.append(f"{name}: malformed function harness")
            for case in spec.cases:
                if not case.description or not case.body or "return" not in case.body:
                    errors.append(f"{name}: malformed function case")
                    break
        else:
            errors.append(f"{name}: unsupported kind {kind!r}")
    return errors


@contextmanager
def _temporary_build_directory(exercise_name: str):
    _BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    path = None
    for _ in range(20):
        candidate = _BUILD_ROOT / f"examshell-{exercise_name}-{secrets.token_hex(8)}"
        try:
            candidate.mkdir()
            path = candidate
            break
        except FileExistsError:
            continue
    if path is None:
        raise OSError("could not allocate a unique C build directory")
    try:
        yield path
    finally:
        # Windows antivirus/indexers can hold a just-executed .exe briefly.
        for delay in (0.0, 0.05, 0.15, 0.3):
            if delay:
                time.sleep(delay)
            try:
                shutil.rmtree(path)
                break
            except FileNotFoundError:
                break
            except OSError:
                continue
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        try:
            _BUILD_ROOT.rmdir()
        except OSError:
            pass


def _copy_submission_to_build(
    exercise_name: str,
    rendu_dir: str | os.PathLike[str],
    build_dir: Path,
) -> list[Path]:
    sources, submitted_headers = _submission_files(exercise_name, rendu_dir)
    copied_sources = []
    for source in sources:
        destination = build_dir / source.name
        shutil.copyfile(source, destination)
        copied_sources.append(destination)
    for header in submitted_headers:
        shutil.copyfile(header, build_dir / header.name)
    for filename, content in _SUPPLIED_HEADERS.get(exercise_name, {}).items():
        (build_dir / filename).write_text(content, encoding="utf-8", newline="\n")
    return copied_sources


def _c_string_literal(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _build_harness(exercise_name: str, token: str) -> str:
    spec = FUNCTION_SPECS[exercise_name]
    case_functions = []
    switch_lines = []
    for index, case in enumerate(spec.cases):
        body = "\n".join(f"    {line}" if line else "" for line in case.body.splitlines())
        case_functions.append(f"static int case_{index}(void)\n{{\n{body}\n}}\n")
        switch_lines.append(f"        case {index}: result = case_{index}(); break;")

    return f"""#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

{spec.prelude}

{''.join(case_functions)}
static int parse_selector(const char *text, int *value)
{{
    char *end = NULL;
    long parsed = strtol(text, &end, 10);
    if (text == end || end == NULL || *end != '\\0' || parsed < 0 || parsed > INT_MAX)
        return 0;
    *value = (int)parsed;
    return 1;
}}

int main(int argc, char **argv)
{{
    int selector;
    int result = 1;
    FILE *status_file;

    if (argc != 3 || !parse_selector(argv[1], &selector))
        return 120;
    switch (selector)
    {{
{chr(10).join(switch_lines)}
        default: return 121;
    }}
    status_file = fopen(argv[2], "wb");
    if (status_file == NULL)
        return 122;
    if (fprintf(status_file, {_c_string_literal(token + ':%d')}, result) < 0)
    {{
        fclose(status_file);
        return 123;
    }}
    if (fclose(status_file) != 0)
        return 124;
    return 0;
}}
"""


def _compiler_flags(build_dir: Path) -> list[str]:
    return [
        "-std=c99",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-fno-builtin",
        "-fno-diagnostics-color",
        "-I",
        str(build_dir),
    ]


def _find_nm(compiler: str, build_dir: Path) -> str | None:
    query = _run_process([compiler, "-print-prog-name=nm"], build_dir, 3.0)
    candidates: list[str] = []
    if (
        query.start_error is None
        and not query.timed_out
        and query.returncode == 0
        and query.stdout
    ):
        value = query.stdout.decode("utf-8", errors="replace").strip()
        if value:
            candidates.append(value)
    candidates.extend(("nm", "llvm-nm"))
    compiler_dir = Path(compiler).resolve().parent
    for candidate in candidates:
        direct = Path(candidate)
        if direct.is_file():
            return str(direct.resolve())
        beside_compiler = compiler_dir / candidate
        if beside_compiler.is_file():
            return str(beside_compiler)
        if os.name == "nt" and beside_compiler.suffix.lower() != ".exe":
            executable_candidate = beside_compiler.with_suffix(".exe")
            if executable_candidate.is_file():
                return str(executable_candidate)
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _parse_nm_symbols(payload: bytes) -> tuple[set[str], set[str]]:
    defined: set[str] = set()
    undefined: set[str] = set()
    for raw_line in payload.decode("utf-8", errors="replace").splitlines():
        fields = raw_line.split()
        if len(fields) < 2:
            continue
        symbol_type = fields[-2]
        symbol = fields[-1]
        if len(symbol_type) != 1:
            continue
        if symbol_type.upper() == "U":
            undefined.add(symbol)
        elif symbol_type not in {"w", "v"}:
            defined.add(symbol)
    return defined, undefined


def _symbol_forms(symbol: str) -> set[str]:
    """Return import/decorated spellings that name the same C symbol."""
    base = symbol.split("@@", 1)[0]
    forms = {base}
    if base.startswith("__imp_"):
        forms.add(base[len("__imp_"):])
    for value in tuple(forms):
        # 32-bit COFF decorates ordinary C names with one leading underscore.
        if value.startswith("_") and not value.startswith("__"):
            forms.add(value[1:])
        if "@" in value and value.rsplit("@", 1)[-1].isdigit():
            forms.add(value.rsplit("@", 1)[0].lstrip("_"))
    return forms


def _is_compiler_runtime_symbol(symbol: str, allowed: set[str]) -> bool:
    raw = symbol.removeprefix("__imp_")
    fixed = {
        "__main",
        "___chkstk_ms",
        "__chkstk_ms",
        "__stack_chk_fail",
        "__stack_chk_guard",
        "__security_cookie",
        "__security_check_cookie",
        "_GLOBAL_OFFSET_TABLE_",
    }
    if raw in fixed:
        return True
    if raw.startswith(("__divdi3", "__udivdi3", "__moddi3", "__umoddi3")):
        return True
    # MinGW implements the public printf family through header wrappers.  The
    # two symbols below are compiler/CRT plumbing for an explicitly allowed
    # printf call, not additional student-facing APIs.
    if "printf" in allowed and raw in {
        "__mingw_vfprintf",
        "__mingw_vprintf",
        "__acrt_iob_func",
    }:
        return True
    return False


def _audit_allowed_functions(
    compiler: str,
    exercise_name: str,
    build_dir: Path,
    sources: Sequence[Path],
    entry_sources: list[Path] | None = None,
) -> str | None:
    """Audit unresolved student-object symbols against the subject whitelist."""
    nm = _find_nm(compiler, build_dir)
    if nm is None:
        return "C symbol inspector 'nm' was not found; allowed functions cannot be verified."

    symbol_groups: list[tuple[Path, set[str], set[str]]] = []
    for index, source in enumerate(sources):
        object_path = build_dir / f"_student_{index}.o"
        compile_result = _run_process(
            [
                compiler,
                *_compiler_flags(build_dir),
                "-c",
                str(source),
                "-o",
                str(object_path),
            ],
            build_dir,
            C_COMPILE_TIMEOUT_SECONDS,
        )
        if compile_result.start_error:
            return f"Could not start C compiler: {compile_result.start_error}"
        if compile_result.timed_out:
            return f"C compilation timed out after {C_COMPILE_TIMEOUT_SECONDS:g}s"
        if compile_result.output_limited:
            return "C compiler produced excessive diagnostic output"
        if compile_result.returncode != 0 or not object_path.is_file():
            diagnostics = compile_result.stderr or compile_result.stdout
            detail = diagnostics.decode("utf-8", errors="replace").strip()
            return f"Compilation failed:\n{detail or 'compiler did not produce an object file'}"

        nm_result = _run_process([nm, "-g", str(object_path)], build_dir, 5.0)
        if nm_result.start_error:
            return f"Could not start C symbol inspector: {nm_result.start_error}"
        if nm_result.timed_out or nm_result.output_limited or nm_result.returncode != 0:
            detail = (nm_result.stderr or nm_result.stdout).decode(
                "utf-8", errors="replace"
            ).strip()
            return f"Could not inspect C symbols: {detail or 'nm failed'}"
        defined, undefined = _parse_nm_symbols(nm_result.stdout)
        symbol_groups.append((source, defined, undefined))

    if entry_sources is not None:
        entry_forms = _symbol_forms(C_EXERCISES[exercise_name]["entry"])
        for source, defined, _ in symbol_groups:
            if any(_symbol_forms(symbol) & entry_forms for symbol in defined):
                entry_sources.append(source)

    defined_forms: set[str] = set()
    for _, defined, _ in symbol_groups:
        for symbol in defined:
            defined_forms.update(_symbol_forms(symbol))
    allowed = set(C_EXERCISES[exercise_name].get("allowed_functions", ()))
    forbidden: set[str] = set()
    for _, _, undefined in symbol_groups:
        for symbol in undefined:
            forms = _symbol_forms(symbol)
            if forms & defined_forms or forms & allowed:
                continue
            if _is_compiler_runtime_symbol(symbol, allowed):
                continue
            # Prefer a clean public-looking spelling in diagnostics.
            clean = min(forms, key=lambda value: (value.startswith("_"), len(value)))
            forbidden.add(clean)
    if not forbidden:
        return None
    allowed_label = ", ".join(sorted(allowed)) if allowed else "none"
    details = "\n".join(f"  - {name}" for name in sorted(forbidden))
    return (
        "Forbidden external function or symbol detected:\n"
        f"{details}\n"
        f"Allowed functions for {exercise_name}: {allowed_label}"
    )


def _check_function_prototype(
    compiler: str,
    exercise_name: str,
    build_dir: Path,
    entry_sources: Sequence[Path],
) -> str | None:
    """Require the submitted definition to match the subject's C prototype.

    Linkers normally match C functions by symbol name alone, so incompatible
    declarations in separate translation units can otherwise link silently.
    Including the defining source and then redeclaring the function with the
    required prototype makes compatibility a standard C constraint that both
    GCC and Clang must diagnose.
    """
    entry = C_EXERCISES[exercise_name]["entry"]
    if not entry_sources:
        return f"Required function definition not found: {entry}"
    if len(entry_sources) != 1:
        return f"Multiple definitions found for required function: {entry}"

    source = entry_sources[0]
    check_path = build_dir / "_examshell_prototype_check.c"
    object_path = build_dir / "_examshell_prototype_check.o"
    required_signature = C_EXERCISES[exercise_name]["signature"].strip()
    check_path.write_text(
        f"#include {_c_string_literal(source.name)}\n"
        f"#undef {entry}\n"
        f"{required_signature}\n",
        encoding="utf-8",
        newline="\n",
    )
    completed = _run_process(
        [
            compiler,
            *_compiler_flags(build_dir),
            "-c",
            str(check_path),
            "-o",
            str(object_path),
        ],
        build_dir,
        C_COMPILE_TIMEOUT_SECONDS,
    )
    if completed.start_error:
        return f"Could not start C compiler for prototype check: {completed.start_error}"
    if completed.timed_out:
        return f"C prototype check timed out after {C_COMPILE_TIMEOUT_SECONDS:g}s"
    if completed.output_limited:
        return "C compiler produced excessive prototype-check diagnostics"
    if completed.returncode != 0 or not object_path.is_file():
        diagnostics = completed.stderr or completed.stdout
        detail = diagnostics.decode("utf-8", errors="replace").strip()
        if not detail:
            detail = f"compiler exited with code {completed.returncode}"
        return f"Required function prototype check failed:\n{detail}"
    return None


def _compile(
    compiler: str,
    build_dir: Path,
    sources: Sequence[Path],
    harness_path: Path | None,
) -> tuple[Path | None, str | None]:
    executable = build_dir / "submission_runner.exe"
    command = [
        compiler,
        *_compiler_flags(build_dir),
        *(str(source) for source in sources),
    ]
    if harness_path is not None:
        command.append(str(harness_path))
    command.extend(("-o", str(executable)))
    completed = _run_process(command, build_dir, C_COMPILE_TIMEOUT_SECONDS)
    if completed.start_error:
        return None, f"Could not start C compiler: {completed.start_error}"
    if completed.timed_out:
        return None, f"C compilation timed out after {C_COMPILE_TIMEOUT_SECONDS:g}s"
    if completed.output_limited:
        return None, "C compiler produced excessive diagnostic output"
    if completed.returncode != 0 or not executable.is_file():
        diagnostics = completed.stderr or completed.stdout
        detail = diagnostics.decode("utf-8", errors="replace").strip()
        if not detail:
            detail = f"compiler exited with code {completed.returncode}"
        return None, f"Compilation failed:\n{detail}"
    return executable, None


def _test_line(index: int, total: int, description: str, passed: bool) -> str:
    status = "PASS" if passed else "FAIL"
    return f"  Test {index:02d}/{total:02d}: {description:<42s} [{status}]"


def _runtime_failure(result: _ProcessResult, case_timeout: float) -> str | None:
    if result.start_error:
        return f"Could not start compiled submission: {result.start_error}"
    if result.timed_out:
        return f"TIMEOUT - test exceeded {case_timeout:g}s"
    if result.output_limited:
        return f"Excessive output (more than {MAX_CAPTURE_BYTES} bytes)"
    if result.returncode != 0:
        suffix = ""
        if result.stderr:
            suffix = f"; stderr: {_display_bytes(result.stderr)}"
        return f"submission exited with code {result.returncode}{suffix}"
    return None


def _grade_program(
    exercise_name: str,
    executable: Path,
    build_dir: Path,
    timeout: float,
) -> tuple[int, int, str]:
    cases = PROGRAM_CASES[exercise_name]
    total = len(cases)
    passed_count = 0
    lines: list[str] = []
    deadline = time.monotonic() + max(0.01, timeout)
    case_limit = min(C_CASE_TIMEOUT_SECONDS, max(0.05, timeout / max(total, 1)))
    # MinGW's CRT may expand wildcard argv entries even with a shell-free
    # CreateProcess call.  Run away from compiler artifacts so the literal '*'
    # operator used by do_op cannot expand into build filenames.
    runtime_dir = build_dir / "_runtime"
    runtime_dir.mkdir()

    for index, case in enumerate(cases, 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result = _ProcessResult(None, b"", b"", timed_out=True)
            run_limit = case_limit
        else:
            run_limit = min(case_limit, remaining)
            result = _run_process([str(executable), *case.argv], runtime_dir, run_limit)
        error = _runtime_failure(result, run_limit)
        actual = _normalize_stdout(result.stdout)
        passed = error is None and actual == _normalize_stdout(case.expected_stdout)
        lines.append(_test_line(index, total, case.description, passed))
        if passed:
            passed_count += 1
        elif error is not None:
            lines.append(f"           Error:    {error}")
        else:
            lines.append(f"           Arguments: {list(case.argv)!r}")
            lines.append(f"           Expected:  {_display_bytes(_normalize_stdout(case.expected_stdout))}")
            lines.append(f"           Got:       {_display_bytes(actual)}")
    return passed_count, total, "\n".join(lines)


def _read_status(path: Path, token: str) -> tuple[int | None, str | None]:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return None, "submission terminated before the test harness completed"
    except OSError as error:
        return None, f"could not read test completion record: {error}"
    expected_prefix = _b(token + ":")
    if len(payload) > 128 or not payload.startswith(expected_prefix):
        return None, "invalid test completion record"
    value = payload[len(expected_prefix):].strip()
    try:
        return int(value.decode("ascii")), None
    except (UnicodeDecodeError, ValueError):
        return None, "invalid test completion status"


def _grade_function(
    exercise_name: str,
    executable: Path,
    build_dir: Path,
    token: str,
    timeout: float,
) -> tuple[int, int, str]:
    cases = FUNCTION_SPECS[exercise_name].cases
    total = len(cases)
    passed_count = 0
    lines: list[str] = []
    deadline = time.monotonic() + max(0.01, timeout)
    case_limit = min(C_CASE_TIMEOUT_SECONDS, max(0.05, timeout / max(total, 1)))

    for zero_index, case in enumerate(cases):
        index = zero_index + 1
        status_path = build_dir / f"case-{zero_index}-{secrets.token_hex(5)}.result"
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result = _ProcessResult(None, b"", b"", timed_out=True)
            run_limit = case_limit
        else:
            run_limit = min(case_limit, remaining)
            result = _run_process(
                [str(executable), str(zero_index), str(status_path)],
                build_dir,
                run_limit,
            )
        error = _runtime_failure(result, run_limit)
        harness_status = None
        if error is None:
            harness_status, status_error = _read_status(status_path, token)
            if status_error:
                error = status_error
        try:
            status_path.unlink(missing_ok=True)
        except OSError:
            pass

        actual_stdout = _normalize_stdout(result.stdout)
        expected_stdout = case.expected_stdout if case.expected_stdout is not None else b""
        output_matches = actual_stdout == _normalize_stdout(expected_stdout)
        passed = error is None and harness_status == 0 and output_matches
        lines.append(_test_line(index, total, case.description, passed))
        if passed:
            passed_count += 1
        elif error is not None:
            lines.append(f"           Error:    {error}")
        elif harness_status != 0:
            lines.append(f"           Expected: {case.expected}")
            lines.append("           Got:      a different result")
        else:
            lines.append(f"           Expected: {_display_bytes(_normalize_stdout(expected_stdout))}")
            lines.append(f"           Got:      {_display_bytes(actual_stdout)}")
    return passed_count, total, "\n".join(lines)


def grade_c_exercise(
    exercise_name: str,
    rendu_dir: str | os.PathLike[str],
    timeout: float = 10,
) -> tuple[int, int, str]:
    """Compile and grade one C submission, returning ``(passed, total, details)``."""
    validation_error = validate_c_submission(exercise_name, rendu_dir)
    if validation_error:
        return 0, 0, validation_error
    compiler = _find_compiler()
    if compiler is None:
        return 0, 0, "C compiler not found. Install GCC/Clang and make the 'cc' command available."
    try:
        numeric_timeout = float(timeout)
    except (TypeError, ValueError):
        numeric_timeout = 10.0
    if numeric_timeout <= 0:
        numeric_timeout = 0.01

    try:
        with _temporary_build_directory(exercise_name) as build_dir:
            sources = _copy_submission_to_build(exercise_name, rendu_dir, build_dir)
            metadata = C_EXERCISES[exercise_name]
            entry_sources: list[Path] = []
            audit_error = _audit_allowed_functions(
                compiler, exercise_name, build_dir, sources, entry_sources
            )
            if audit_error:
                return 0, 0, audit_error
            if metadata["kind"] == "function":
                prototype_error = _check_function_prototype(
                    compiler, exercise_name, build_dir, entry_sources
                )
                if prototype_error:
                    return 0, 0, prototype_error
            link_sources = list(sources)
            if metadata["kind"] == "program" and os.name == "nt":
                # MinGW-w64 enables argv wildcard expansion in its startup
                # object.  A literal '*' (the do_op multiplication operator)
                # would otherwise disappear or become build filenames.
                no_glob_source = build_dir / "_examshell_no_glob.c"
                no_glob_source.write_text(
                    "int _dowildcard = 0;\n", encoding="utf-8", newline="\n"
                )
                link_sources.append(no_glob_source)
            harness_path = None
            token = ""
            if metadata["kind"] == "function":
                token = secrets.token_hex(24)
                harness_path = build_dir / "_examshell_harness.c"
                harness_path.write_text(
                    _build_harness(exercise_name, token),
                    encoding="utf-8",
                    newline="\n",
                )
            executable, compile_error = _compile(
                compiler, build_dir, link_sources, harness_path
            )
            if compile_error:
                return 0, 0, compile_error
            if metadata["kind"] == "program":
                return _grade_program(
                    exercise_name, executable, build_dir, numeric_timeout
                )
            return _grade_function(
                exercise_name, executable, build_dir, token, numeric_timeout
            )
    except OSError as error:
        return 0, 0, f"Could not prepare temporary C build: {error}"


__all__ = (
    "grade_c_exercise",
    "validate_c_specs",
    "validate_c_submission",
)
