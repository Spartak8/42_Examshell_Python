# Exam Shell

Exam Shell is a terminal-based simulator for practicing 42-style Python exams. It includes Exam 03 and Exam 04, timed real-exam sessions, unrestricted practice sessions, automatic grading, test traces, and exercise subjects.

## Requirements

- Python 3.10 or newer
- A terminal that supports ANSI colors
- No external Python packages are required
- `make` is optional and only needed for the Makefile shortcuts

Keep `examshell.py` and `exam_worker.py` together in the same directory. `exam_worker.py` is used internally to run submitted solutions safely and should not be started manually.

## Starting Exam Shell

Open a terminal in the project directory and run:

```bash
python examshell.py
```

If your system provides `make` and `python3`, you can start it with:

```bash
make run
```

The interactive setup will ask you to choose:

1. Exam 03 or Exam 04
2. Real Exam or Practice mode
3. A level and exercise when using Practice mode

You can also skip parts of the menus with command-line options:

```bash
python examshell.py --practice
python examshell.py --real
python examshell.py --exam 3
python examshell.py --exam 4
python examshell.py --exam 3 --practice
python examshell.py --exam 4 --real
```

Equivalent Makefile shortcuts are available:

```bash
make practice
make real
make exam03
make exam04
```

Run `make help` to display all available targets. All Makefile targets use the `python3` command.

## Modes

### Real Exam

- Runs for three hours.
- Assigns one random exercise from Level 1.
- Passing an exercise advances you to the next level.
- Passing every level completes the exam with 100 points.
- The timer continues while Exam Shell waits for commands and level confirmation.

### Practice

- Has no timer or score.
- Lets you choose any level and exercise.
- Use the `menu` command to switch exercises at any time.
- After passing an exercise, you can immediately select another one.

## Exercise files

When an exercise is assigned, Exam Shell creates its subject at:

```text
subject/<exercise>/<exercise>.txt
```

Create your solution using this exact structure:

```text
rendu/<exercise>/<exercise>.py
```

For example, for `py_inter`:

```text
subject/py_inter/py_inter.txt
rendu/py_inter/py_inter.py
```

The function name inside the solution must exactly match the function shown in the subject.

> **Important:** `subject/`, `rendu/`, and `traces/` are temporary session directories. Exam Shell removes them when the session finishes. Copy any solution you want to keep somewhere else before exiting.

## Commands

| Command | Description |
| --- | --- |
| `grademe` | Run all tests for the current solution. `grade` is also accepted. |
| `subject` | Display the current subject in the terminal. |
| `trace` | Display the latest grading trace. |
| `trace N` | Display trace attempt number `N` for the current exercise. |
| `status` | Show the current exercise, score or solved count, and attempts. |
| `time` | Show the remaining time, or confirm that Practice has no limit. |
| `menu` | Choose another exercise in Practice mode. |
| `clear` | Clear the terminal and redraw the session banner. |
| `help` | Show the available commands. |
| `exit` | Finish the current session after confirmation. |

## Grading

Type `grademe` after creating your solution file. Exam Shell checks:

- The expected file exists.
- The source contains valid Python syntax.
- The required function is declared with normal `def`.
- Exercise-specific forbidden functions are not used.
- The function completes within the grading safety timeout.
- The returned value and its type match the expected result.
- Every configured test case passes.

Student code runs through `exam_worker.py` in a separate process. An exception, infinite loop, `exit()`, or unwanted `print()` output from a solution will not freeze or corrupt the main Exam Shell.

Cryptic Sorter has an additional rule: `sorted()` and `.sort()` are forbidden. Its sorting algorithm must be implemented manually.

After each valid grading attempt, a detailed report is saved under `traces/`. Failed cases show the call, expected result, actual result, or runtime error.

## Project structure

```text
exam1/
├── examshell.py              Main application, subjects, and exercise cases
├── exam_worker.py            Internal isolated submission runner
├── Makefile                  Short commands for running and testing
├── README.md                 Usage guide
└── tests/
    └── test_examshell.py     Regression tests for Exam Shell itself
```

The tests in `tests/` verify the Exam Shell application. They are separate from the exercise cases used when a student enters `grademe`.

## Running project tests

After changing Exam Shell, run:

```bash
python -m unittest discover -s tests -v
```

Or use the Makefile target, which runs the same suite with `python3`:

```bash
make test
```

The regression suite checks configuration completeness, all exercise reference implementations, strict result types, timers, practice attempts, forbidden functions, exceptions, printed output, and infinite-loop termination.

## Common problems

### File not found

Check that both the directory and filename exactly match the assigned exercise:

```text
rendu/<exercise>/<exercise>.py
```

### Function not found

Open the subject and use the exact function signature it provides. Do not rename the required function or declare it with `async def`.

### Internal runner not found

Make sure `exam_worker.py` is in the same directory as `examshell.py`.

### A solution times out

Check for infinite loops or an algorithm that is too slow. Each complete grading run has a ten-second safety timeout.
