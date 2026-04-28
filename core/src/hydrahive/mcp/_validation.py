from __future__ import annotations


class McpValidationError(ValueError):
    pass


_VALID_TRANSPORTS = {"stdio", "http", "sse"}


def validate_transport(transport: str) -> None:
    if transport not in _VALID_TRANSPORTS:
        raise McpValidationError(
            f"Ungültiger Transport: '{transport}' (erlaubt: {', '.join(_VALID_TRANSPORTS)})"
        )


def validate_name(name: str) -> None:
    if not name or not name.strip():
        raise McpValidationError("Name darf nicht leer sein")
    if len(name) > 100:
        raise McpValidationError("Name zu lang (max 100 Zeichen)")


def validate_id(server_id: str) -> None:
    if not server_id or not server_id.strip():
        raise McpValidationError("ID darf nicht leer sein")
    if not all(c.isalnum() or c in "-_" for c in server_id):
        raise McpValidationError("ID nur a-z A-Z 0-9 _ - erlaubt")
    if len(server_id) > 64:
        raise McpValidationError("ID zu lang (max 64 Zeichen)")


def validate_stdio_config(config: dict) -> None:
    cmd = config.get("command")
    if not cmd:
        raise McpValidationError("stdio-Server: command fehlt")
    if not isinstance(cmd, str):
        raise McpValidationError("stdio-Server: command muss ein String sein")
    args = config.get("args", [])
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise McpValidationError("stdio-Server: args muss list[str] sein")
    env = config.get("env", {})
    if not isinstance(env, dict):
        raise McpValidationError("stdio-Server: env muss dict sein")


def validate(config: dict) -> None:
    validate_id(config.get("id", ""))
    validate_name(config.get("name", ""))
    transport = config.get("transport", "")
    validate_transport(transport)
    if transport == "stdio":
        validate_stdio_config(config)
    elif transport in ("http", "sse"):
        if not config.get("url"):
            raise McpValidationError(f"{transport}-Server: url fehlt")
