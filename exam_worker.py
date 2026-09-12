#!/usr/bin/env python3
"""Isolated submission runner used internally by examshell.py."""

import contextlib
import os
import sys
import types
from pathlib import Path


# ``python -I`` intentionally omits the script directory from sys.path.  Load
# only this trusted sibling module, then remove the temporary search entry
# before importing a submission.
_WORKER_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, _WORKER_DIR)
try:
    from worker_protocol import (
        MAX_MESSAGE_BYTES,
        MAX_SOURCE_BYTES,
        ProtocolError,
        decode_request,
        encode_error_response,
        encode_success_response,
        error_result,
        success_result,
    )
finally:
    del sys.path[0]


def _error_message(error):
    """Return a bounded, best-effort description of an arbitrary exception."""
    if isinstance(error, (KeyboardInterrupt, SystemExit)):
        return f"{type(error).__name__}: submission stopped execution"
    try:
        detail = str(error)
    except BaseException:
        detail = "<exception message unavailable>"
    return f"{type(error).__name__}: {detail}"


def _read_submission_source(file_path):
    """Read the validated source again without consulting a bytecode cache."""
    with file_path.open("rb") as source_file:
        source_bytes = source_file.read(MAX_SOURCE_BYTES + 1)
    if len(source_bytes) > MAX_SOURCE_BYTES:
        raise ValueError(f"submission source exceeds {MAX_SOURCE_BYTES} bytes")
    try:
        return source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"submission source is not valid UTF-8 near byte {error.start}"
        ) from error


def execute_submission(file_path, function_name, test_arguments):
    """Load a submission once and execute its complete test batch."""
    module_name = f"_exam_submission_{os.getpid()}"
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            source = _read_submission_source(file_path)
            module = types.ModuleType(module_name)
            module.__file__ = str(file_path)
            module.__package__ = None
            sys.modules[module_name] = module
            try:
                code = compile(source, str(file_path), "exec", dont_inherit=True)
                exec(code, module.__dict__)

                function = getattr(module, function_name, None)
                if not callable(function):
                    raise TypeError(f"'{function_name}' is not a callable function")

                results = []
                for arguments in test_arguments:
                    try:
                        result = function(*arguments)
                    except BaseException as error:
                        results.append(error_result(_error_message(error), arguments))
                        continue

                    same_as_first = bool(arguments) and result is arguments[0]
                    try:
                        results.append(success_result(result, arguments, same_as_first))
                    except ProtocolError as error:
                        results.append(error_result(
                            f"Could not serialize function result: {error}",
                            arguments,
                        ))
                return results
            finally:
                if sys.modules.get(module_name) is module:
                    del sys.modules[module_name]


def _write_response(response_path, payload):
    """Write a bounded response to the dedicated parent-created channel."""
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ProtocolError("worker response exceeds the size limit")
    flags = os.O_WRONLY | os.O_TRUNC | getattr(os, "O_BINARY", 0)
    descriptor = os.open(response_path, flags)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("could not write worker response")
            view = view[written:]
    finally:
        os.close(descriptor)


def main():
    if len(sys.argv) != 4:
        return 2

    file_path = Path(sys.argv[1]).resolve()
    function_name = sys.argv[2]
    response_path = sys.argv[3]

    try:
        request = sys.stdin.buffer.read(MAX_MESSAGE_BYTES + 1)
        test_arguments = decode_request(request)
        results = execute_submission(file_path, function_name, test_arguments)
        try:
            payload = encode_success_response(results)
        except ProtocolError as error:
            payload = encode_error_response(f"Could not serialize function result: {error}")
    except BaseException as error:
        payload = encode_error_response(_error_message(error))

    try:
        _write_response(response_path, payload)
    except BaseException:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
