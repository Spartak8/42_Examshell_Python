#!/usr/bin/env python3
"""Strict, size-bounded JSON protocol for the isolated Python grader.

The worker executes untrusted submissions, so its response must be treated as
untrusted input.  This module deliberately supports only the value types used
by the exams and represents each value with an explicit type tag.  In
particular, no Python object deserialization (such as pickle) is involved.
"""

import json
import re


PROTOCOL_NAME = "exam-worker"
PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 1024 * 1024
MAX_VALUE_DEPTH = 64
MAX_VALUE_NODES = 100_000
MAX_BATCH_RESULTS = 1_000
MAX_ERROR_CHARS = 4_096
MAX_INTEGER_DIGITS = 4_300

_INTEGER_RE = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")


class ProtocolError(ValueError):
    """Raised when a worker request or response violates the protocol."""


class _ValueBudget:
    def __init__(self):
        self.nodes = 0

    def consume(self, depth):
        if depth > MAX_VALUE_DEPTH:
            raise ProtocolError("value nesting is too deep")
        self.nodes += 1
        if self.nodes > MAX_VALUE_NODES:
            raise ProtocolError("value contains too many items")


def _encode_value(value, budget, active_containers, depth):
    budget.consume(depth)
    value_type = type(value)

    if value is None:
        return {"type": "none"}
    if value_type is bool:
        return {"type": "bool", "value": value}
    if value_type is int:
        try:
            text = str(value)
        except (ValueError, OverflowError) as error:
            raise ProtocolError(f"integer cannot be encoded: {error}") from error
        if len(text.lstrip("-")) > MAX_INTEGER_DIGITS:
            raise ProtocolError("integer contains too many digits")
        return {"type": "int", "value": text}
    if value_type is float:
        return {"type": "float", "value": value.hex()}
    if value_type is str:
        return {"type": "str", "value": value}

    if value_type not in (list, tuple, dict):
        raise ProtocolError(f"unsupported value type: {value_type.__name__}")

    identity = id(value)
    if identity in active_containers:
        raise ProtocolError("cyclic containers are not supported")
    active_containers.add(identity)
    try:
        if value_type is dict:
            items = [
                [
                    _encode_value(key, budget, active_containers, depth + 1),
                    _encode_value(item, budget, active_containers, depth + 1),
                ]
                for key, item in value.items()
            ]
            return {"type": "dict", "items": items}

        items = [
            _encode_value(item, budget, active_containers, depth + 1)
            for item in value
        ]
        return {"type": "list" if value_type is list else "tuple", "items": items}
    finally:
        active_containers.remove(identity)


def encode_value(value):
    """Convert supported Python values to a tagged, JSON-compatible tree."""
    return _encode_value(value, _ValueBudget(), set(), 0)


def _expect_exact_keys(value, expected, context):
    if type(value) is not dict or set(value) != set(expected):
        raise ProtocolError(f"invalid {context} fields")


def _decode_value(node, budget, depth):
    budget.consume(depth)
    if type(node) is not dict or type(node.get("type")) is not str:
        raise ProtocolError("invalid typed value")

    value_type = node["type"]
    if value_type == "none":
        _expect_exact_keys(node, ("type",), "none value")
        return None

    if value_type in ("bool", "int", "float", "str"):
        _expect_exact_keys(node, ("type", "value"), f"{value_type} value")
        value = node["value"]
        if value_type == "bool":
            if type(value) is not bool:
                raise ProtocolError("invalid bool value")
            return value
        if value_type == "str":
            if type(value) is not str:
                raise ProtocolError("invalid string value")
            return value
        if type(value) is not str:
            raise ProtocolError(f"invalid {value_type} representation")
        if value_type == "int":
            digits = value.lstrip("-")
            if (
                not _INTEGER_RE.fullmatch(value)
                or len(digits) > MAX_INTEGER_DIGITS
            ):
                raise ProtocolError("invalid integer representation")
            try:
                return int(value)
            except (ValueError, OverflowError) as error:
                raise ProtocolError("invalid integer representation") from error

        try:
            decoded_float = float.fromhex(value)
        except (ValueError, OverflowError) as error:
            raise ProtocolError("invalid float representation") from error
        if decoded_float.hex() != value:
            raise ProtocolError("non-canonical float representation")
        return decoded_float

    if value_type not in ("list", "tuple", "dict"):
        raise ProtocolError(f"unknown value type: {value_type}")
    _expect_exact_keys(node, ("type", "items"), f"{value_type} value")
    items = node["items"]
    if type(items) is not list:
        raise ProtocolError(f"invalid {value_type} items")

    if value_type in ("list", "tuple"):
        decoded = [_decode_value(item, budget, depth + 1) for item in items]
        return decoded if value_type == "list" else tuple(decoded)

    decoded = {}
    for pair in items:
        if type(pair) is not list or len(pair) != 2:
            raise ProtocolError("invalid dictionary item")
        key = _decode_value(pair[0], budget, depth + 1)
        item = _decode_value(pair[1], budget, depth + 1)
        try:
            if key in decoded:
                raise ProtocolError("duplicate dictionary key")
            decoded[key] = item
        except TypeError as error:
            raise ProtocolError("unhashable dictionary key") from error
    return decoded


def decode_value(node):
    """Decode and validate one tagged value tree."""
    return _decode_value(node, _ValueBudget(), 0)


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_json_constant(value):
    raise ProtocolError(f"invalid JSON constant: {value}")


def _load_json(payload):
    if type(payload) is not bytes:
        raise ProtocolError("protocol payload must be bytes")
    if not payload:
        raise ProtocolError("empty protocol payload")
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ProtocolError("protocol payload exceeds the size limit")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProtocolError("protocol payload is not valid UTF-8") from error
    if text.startswith("\ufeff"):
        raise ProtocolError("protocol payload must not contain a BOM")
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, RecursionError, ValueError) as error:
        raise ProtocolError("protocol payload is not valid JSON") from error


def _dump_json(message):
    try:
        payload = json.dumps(
            message,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ProtocolError(f"could not encode protocol payload: {error}") from error
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ProtocolError("protocol payload exceeds the size limit")
    return payload


def encode_request(test_arguments):
    """Serialize the parent's list of positional-argument tuples."""
    if type(test_arguments) is not list:
        raise ProtocolError("test argument batch must be a list")
    if len(test_arguments) > MAX_BATCH_RESULTS:
        raise ProtocolError("test argument batch is too large")
    encoded_arguments = []
    for arguments in test_arguments:
        if type(arguments) is not tuple:
            raise ProtocolError("each test argument set must be a tuple")
        encoded_arguments.append(encode_value(arguments))
    return _dump_json({
        "protocol": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "arguments": encoded_arguments,
    })


def decode_request(payload):
    """Parse and validate a request inside the worker."""
    message = _load_json(payload)
    _expect_exact_keys(message, ("protocol", "version", "arguments"), "request")
    if (
        type(message["protocol"]) is not str
        or message["protocol"] != PROTOCOL_NAME
        or type(message["version"]) is not int
        or message["version"] != PROTOCOL_VERSION
    ):
        raise ProtocolError("unsupported worker protocol")
    encoded_arguments = message["arguments"]
    if type(encoded_arguments) is not list or len(encoded_arguments) > MAX_BATCH_RESULTS:
        raise ProtocolError("invalid test argument batch")
    arguments = []
    for encoded in encoded_arguments:
        decoded = decode_value(encoded)
        if type(decoded) is not tuple:
            raise ProtocolError("each test argument set must decode to a tuple")
        arguments.append(decoded)
    return arguments


def _bounded_error(message):
    if type(message) is not str:
        message = "Unknown worker error"
    safe_characters = []
    safe_length = 0
    truncated = False
    for index, character in enumerate(message):
        codepoint = ord(character)
        if (
            codepoint < 32
            or 127 <= codepoint <= 159
            or 0x202A <= codepoint <= 0x202E
            or 0x2066 <= codepoint <= 0x2069
        ):
            if codepoint <= 0xFF:
                safe_character = f"\\x{codepoint:02x}"
            elif codepoint <= 0xFFFF:
                safe_character = f"\\u{codepoint:04x}"
            else:
                safe_character = f"\\U{codepoint:08x}"
        else:
            safe_character = character
        remaining = MAX_ERROR_CHARS - safe_length
        if len(safe_character) > remaining:
            safe_characters.append(safe_character[:remaining])
            truncated = True
            break
        safe_characters.append(safe_character)
        safe_length += len(safe_character)
        if safe_length == MAX_ERROR_CHARS:
            truncated = index + 1 < len(message)
            break
    safe_message = "".join(safe_characters)
    return safe_message + "..." if truncated else safe_message


def _validate_error(message, context):
    if (
        type(message) is not str
        or not message
        or len(message) > MAX_ERROR_CHARS + 3
        or _bounded_error(message) != message
    ):
        raise ProtocolError(f"invalid {context}")
    return message


def success_result(result, arguments_after, same_as_first_argument):
    """Build one successful, fully typed worker result item."""
    if type(arguments_after) is not tuple:
        raise ProtocolError("post-call arguments must be a tuple")
    if type(same_as_first_argument) is not bool:
        raise ProtocolError("result identity flag must be a bool")
    return {
        "ok": True,
        "result": encode_value(result),
        "arguments_after": encode_value(arguments_after),
        "same_as_first_argument": same_as_first_argument,
    }


def error_result(error, arguments_after):
    """Build one failed worker result item."""
    if type(arguments_after) is not tuple:
        raise ProtocolError("post-call arguments must be a tuple")
    return {
        "ok": False,
        "error": _bounded_error(error),
        "arguments_after": encode_value(arguments_after),
        "same_as_first_argument": False,
    }


def encode_success_response(results):
    """Serialize a worker batch response made of pre-encoded result items."""
    if type(results) is not list or len(results) > MAX_BATCH_RESULTS:
        raise ProtocolError("invalid worker result batch")
    return _dump_json({
        "protocol": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "ok": True,
        "results": results,
    })


def encode_error_response(error):
    """Serialize a top-level worker failure."""
    return _dump_json({
        "protocol": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "ok": False,
        "error": _bounded_error(error),
    })


def decode_response(payload, expected_results):
    """Validate every worker result and return a native-value envelope."""
    if (
        type(expected_results) is not int
        or expected_results < 0
        or expected_results > MAX_BATCH_RESULTS
    ):
        raise ProtocolError("invalid expected result count")
    message = _load_json(payload)
    if type(message) is not dict:
        raise ProtocolError("invalid result envelope")
    if (
        type(message.get("protocol")) is not str
        or message.get("protocol") != PROTOCOL_NAME
        or type(message.get("version")) is not int
        or message.get("version") != PROTOCOL_VERSION
    ):
        raise ProtocolError("unsupported worker protocol")
    if type(message.get("ok")) is not bool:
        raise ProtocolError("invalid result envelope status")

    if not message["ok"]:
        _expect_exact_keys(
            message, ("protocol", "version", "ok", "error"), "error envelope"
        )
        error = _validate_error(message["error"], "worker error")
        return {"ok": False, "error": error}

    _expect_exact_keys(
        message, ("protocol", "version", "ok", "results"), "result envelope"
    )
    encoded_results = message["results"]
    if type(encoded_results) is not list or len(encoded_results) != expected_results:
        raise ProtocolError("incomplete test result batch")

    results = []
    for encoded in encoded_results:
        if type(encoded) is not dict or type(encoded.get("ok")) is not bool:
            raise ProtocolError("invalid test result item")
        common_fields = (
            "ok",
            "arguments_after",
            "same_as_first_argument",
        )
        if encoded["ok"]:
            _expect_exact_keys(encoded, common_fields + ("result",), "successful result item")
        else:
            _expect_exact_keys(encoded, common_fields + ("error",), "failed result item")

        arguments_after = decode_value(encoded["arguments_after"])
        if type(arguments_after) is not tuple:
            raise ProtocolError("post-call arguments must decode to a tuple")
        same_as_first_argument = encoded["same_as_first_argument"]
        if type(same_as_first_argument) is not bool:
            raise ProtocolError("invalid result identity flag")

        if encoded["ok"]:
            results.append({
                "ok": True,
                "result": decode_value(encoded["result"]),
                "arguments_after": arguments_after,
                "same_as_first_argument": same_as_first_argument,
            })
        else:
            error = _validate_error(encoded["error"], "test result error")
            if same_as_first_argument:
                raise ProtocolError("failed result cannot have a true identity flag")
            results.append({
                "ok": False,
                "error": error,
                "arguments_after": arguments_after,
                "same_as_first_argument": False,
            })
    return {"ok": True, "results": results}
