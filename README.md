# Exam Shell

Exam Shell is a terminal simulator for 42-style programming exams. It includes Exam Rank 02 in C plus Exam 03 and Exam 04 in Python, with timed real-exam sessions, unrestricted practice, automatic grading, traces, and local subjects.

## Requirements

- Python 3.10 or newer
- A terminal with ANSI-color support
- For Exam 02: `cc` on `PATH` (GCC or Clang with C99 support), plus `nm`
  or `llvm-nm` from the same toolchain for allowed-function checks
- No external Python packages
- `make` is optional and is used only for shortcuts

Keep `examshell.py`, `exam_worker.py`, `worker_protocol.py`, `exam02_catalog.py`, `exam02_subjects.py`, and `c_grader.py` together. Exam 02 subject text is embedded in the project; the original downloaded exercise archive is not required.

## Starting Exam Shell

```bash
python examshell.py
```

The interactive setup asks for an exam, then Real Exam or Practice mode. Practice mode also lets you choose a level and exercise immediately.

Command-line examples:

```bash
python examshell.py --practice
python examshell.py --real
python examshell.py --exam 2
python examshell.py --exam 3 --practice
python examshell.py --exam 4 --real
```

Equivalent shortcuts:

```bash
make run
make practice
make real
make exam02
make exam03
make exam04
```

Run `make help` to list every target.

## Modes

### Real Exam

- Runs for three hours.
- Assigns one random exercise from Level 1.
- Passing advances to the next level.
- Completing every level earns 100 points.
- Exam 02 has four 25-point levels; its pool contains 57 C exercises.

### Practice

- Has no timer or score.
- Lets you choose any level and exercise.
- Use `menu` to switch exercises at any time.

## Exercise files

Each assigned subject is written to:

```text
subject/<exercise>/<exercise>.txt
```

Submit using the exact language-specific filename:

```text
# Exam 02 (C)
rendu/<exercise>/<exercise>.c

# Exam 03 or 04 (Python)
rendu/<exercise>/<exercise>.py
```

Examples:

```text
subject/ft_strlen/ft_strlen.txt
rendu/ft_strlen/ft_strlen.c

subject/py_inter/py_inter.txt
rendu/py_inter/py_inter.py
```

Some C assignments require a header as stated in their subject. Grader-provided headers such as `list.h` are placed with the subject when the assignment is selected.

> **Important:** `subject/`, `rendu/`, and `traces/` are temporary session directories. They are removed when the session finishes, so copy solutions you want to keep before exiting.

## Commands

| Command | Description |
| --- | --- |
| `grademe` | Compile/run all tests for the current solution (`grade` also works). |
| `subject` | Display the current subject. |
| `trace` | Display the latest grading trace. |
| `trace N` | Display attempt `N` for the current exercise. |
| `status` | Show the current exercise, score or solved count, and attempts. |
| `time` | Show remaining time or confirm that Practice has no limit. |
| `menu` | Choose another exercise in Practice mode. |
| `clear` | Clear the terminal and redraw the session banner. |
| `help` | Show available commands. |
| `exit` | Finish the current session after confirmation. |

## Grading

Python submissions are syntax-checked and executed through `exam_worker.py` in a separate process. Worker messages use a bounded, schema-validated protocol, results are type-strict, and exercise-specific restrictions such as the Cryptic Sorter sorting prohibition are enforced.

C submissions are compiled with strict warnings using C99, `-Wall`, `-Wextra`, and `-Werror`. Standalone programs are checked by exact output and exit status. Function exercises are linked to generated test harnesses that check return values, mutations, allocation results, lists, and grids as appropriate. Each native test runs in a separate process with a timeout, so ordinary crashes and infinite loops are reported without terminating Exam Shell.

Expected C results are defined independently by the simulator and never loaded from example solutions.

Submission execution is process-isolated for timeout reliability, but neither the Python nor C runner is a security, filesystem, network, or memory sandbox. Only grade code you trust on your own machine.

After each valid attempt, the full report is saved under `traces/`. Output is compared exactly, including spaces and final newlines.

## Project structure

```text
exam1/
├── examshell.py          Main application and Python exercise data
├── exam_worker.py        Isolated Python submission runner
├── worker_protocol.py    Bounded protocol for the Python runner
├── exam02_catalog.py     Exam 02 registry and subject loader
├── exam02_subjects.py    Embedded Exam 02 subject text
├── c_grader.py           Native C compiler/test runner
├── Makefile              Command shortcuts
└── README.md             Usage guide
```

## Common problems

### File not found

Check both the directory and filename. Exam 02 requires `.c`; Exams 03 and 04 require `.py`.

### `cc` not found

Install GCC or Clang and confirm `cc --version` works in the same terminal before starting Exam 02.

### Compilation failed

Fix every compiler error and warning. Warnings are errors under the Exam 02 grading flags.

### Function not found

Use the exact function name and prototype shown in the subject. Python functions must use normal `def` rather than `async def`.

### A solution times out

Check for infinite loops, runaway recursion, or an algorithm that is too slow. The trace identifies the timed-out case.
