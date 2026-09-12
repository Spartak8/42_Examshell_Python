#!/usr/bin/env python3
"""Isolated submission runner used internally by examshell.py."""

import contextlib
import importlib.util
import os
import pickle
import sys
import traceback
from pathlib import Path


def execute_submission(file_path, function_name, test_arguments):
    """Load a submission once and execute its complete test batch."""
    module_name = f"_exam_submission_{os.getpid()}"
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load submission file: {file_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            function = getattr(module, function_name, None)
            if not callable(function):
                raise TypeError(f"'{function_name}' is not a callable function")

            results = []
            for args in test_arguments:
                try:
                    results.append({"ok": True, "result": function(*args)})
                except BaseException as error:
                    if isinstance(error, (KeyboardInterrupt, SystemExit)):
                        message = f"{type(error).__name__}: submission stopped execution"
                    else:
                        message = f"{type(error).__name__}: {error}"
                    results.append({"ok": False, "error": message})
            return results


def send_response(response):
    """Write exactly one binary response for the parent exam process."""
    try:
        payload = pickle.dumps(response, protocol=pickle.HIGHEST_PROTOCOL)
    except BaseException as error:
        payload = pickle.dumps({
            "ok": False,
            "error": f"Could not serialize function result: {type(error).__name__}: {error}",
        })
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def main():
    if len(sys.argv) != 3:
        send_response({"ok": False, "error": "Invalid worker arguments"})
        return 2

    file_path = Path(sys.argv[1]).resolve()
    function_name = sys.argv[2]

    try:
        test_arguments = pickle.loads(sys.stdin.buffer.read())
        results = execute_submission(file_path, function_name, test_arguments)
        send_response({"ok": True, "results": results})
        return 0
    except BaseException as error:
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            message = f"{type(error).__name__}: submission stopped execution"
        else:
            message = f"{type(error).__name__}: {error}"
        send_response({
            "ok": False,
            "error": message,
            "traceback": traceback.format_exc(limit=3),
        })
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
