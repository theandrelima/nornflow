"""Hidden Nox easter egg for `nornflow show --nox`."""

import typer
from termcolor import colored

NOX_FACE = """\
                                      ██                  ██
                                    ██▒▒██              ██▒▒██
                                    ██▒▒▒▒██          ██▒▒▒▒██
                                    ██▒▒▒▒████      ████▒▒▒▒██
                                    ██▒▒▒▒▒▒▒▒██████▒▒▒▒▒▒▒▒██
                                    ██▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒██
                                    ██▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒██
                                  ██▒▒▒▒▒▒██▒▒▒▒▒▒▒▒▒▒██▒▒▒▒▒▒██
                                ██░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░██
                                ██░░░░░░▒▒▒▒▒▒░░██░░▒▒▒▒▒▒░░░░░░██
                                  ██░░░░░░░░░░░░░░░░░░░░░░░░░░██
                                    ██░░░░░░░░██████░░░░░░░░██
                                      ██░░░░░░░░░░░░░░░░░░██
                                        ████░░░░░░░░░░████
                                      ██▓▓░░██████████░░▒▒██
                                    ██▓▓▒▒░░░░░░░░░░░░░░▒▒▒▒██
                                    ██▓▓▒▒▒▒░░░░░░░░░░▒▒▒▒▒▒██
                                    ██▓▓▒▒▒▒░░░░░░░░░░▒▒▒▒▒▒██
                                    ██▒▒▒▒▒▒▒▒░░░░░░▒▒▒▒▒▒▒▒██
                ██████████        ██▓▓▒▒▒▒▒▒▒▒░░░░░░▒▒▒▒▒▒▒▒▒▒██
            ████▓▓▓▓▓▓▓▓▓▓██████████▓▓▒▒▒▒██▒▒▒▒░░▒▒▒▒██▒▒▒▒▒▒██
          ██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓▒▒▒▒██▒▒░░░░░░▒▒██▒▒▒▒▒▒▒▒██
          ██▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▓▓▒▒▒▒▒▒██▒▒░░░░░░▒▒██▒▒▒▒██▒▒██
        ██▓▓▓▓▒▒▓▓▒▒▒▒▒▒▒▒▒▒██████▒▒▒▒▒▒▒▒██▒▒██░░██▒▒██▒▒██▒▒▒▒██
        ██▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒██  ██████████▒▒██████████████▒▒████▒▒██
        ██▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒████░░░░░░░░░░████████  ██████▒▒██████
        ██▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░░████  ████████████
        ██▓▓▓▓▓▓▒▒▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░▒▒░░░░░░░░██  ████
        ██▓▓▓▓▓▓▓▓▓▓▒▒▓▓▒▒▒▒▒▒▒▒▒▒▒▒░░████░░░░██
          ████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒██    ██░░██
              ██████████████████████        ████"""

NOX_POEM = """Across the hush of frozen streams,
where moonlit signals glow,
a white fox runs through silver dreams,
the quiet spark of hope.

With ears brushed blue by polar light,
and tail in frost-blue frame,
it traces paths through tangled night,
and calls each route by name.

Upon its collar, purple-bright,
an arrowed N takes flight;
a bolt, a rune, a northern sign,
cut sharp against the white.

It does not bark. It does not boast.
It moves with measured grace,
through woven paths and hidden posts,
it finds the cleanest trace.

Where Nornir weave the threads of fate,
beneath the aurora's glow,
Nox charts the paths they ordinate —
and sets them all in flow."""


def _poem_width() -> int:
    """Width of the longest poem line."""
    lines = [line for line in NOX_POEM.splitlines() if line]
    return max(len(line) for line in lines) if lines else 0


def _center_pad(line: str, width: int) -> tuple[str, str]:
    """Return left and right space padding to center line within width."""
    if len(line) >= width:
        return "", ""
    pad = width - len(line)
    left = pad // 2
    return " " * left, " " * (pad - left)


def _nox_face_lines() -> list[str]:
    """Return the block-art fox as individual lines."""
    return NOX_FACE.splitlines()


def _display_width() -> int:
    """Shared width for centering the fox block and poem together."""
    face_lines = _nox_face_lines()
    face_width = max(len(line) for line in face_lines) if face_lines else 0
    return max(face_width, _poem_width())


def _face_block_pad(display_width: int) -> str:
    """Left pad so the fox art block is centered above the poem."""
    face_width = max(len(line) for line in _nox_face_lines()) if _nox_face_lines() else 0
    if display_width <= face_width:
        return ""
    return " " * ((display_width - face_width) // 2)


def print_nox() -> None:
    """Print Nox's ASCII face and poem to stdout."""
    fox = {"color": "cyan", "attrs": ["bold"]}
    width = _display_width()
    face_pad = _face_block_pad(width)

    for line in _nox_face_lines():
        typer.echo(face_pad + colored(line, **fox))

    typer.echo()
    for line in NOX_POEM.splitlines():
        if not line:
            typer.echo()
            continue
        left, right = _center_pad(line, width)
        typer.echo(left + line + right)
