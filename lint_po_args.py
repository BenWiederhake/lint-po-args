#!/usr/bin/env python3

"""
Checks for grave translation errors and typos, like translating "please use
the -0 option" as "bitte nutze die -O Option", which is a different
command-line option and likely won't work.
In particular, this script checks:
- Command-line flags
- printf-style format instructions
See the regex for details.
"""

import argparse
import collections
from typing import Any, List, Optional
import re


RE_PRINTFISH = re.compile(r"%[0-9a-zA-Z+-]+", re.M)
RE_CMDLINE_OPTION = re.compile(r"(?<![0-9a-zA-Z_-])-[0-9a-zA-Z_-]+", re.M)
# In-line unit test:
assert RE_PRINTFISH.findall("-foo bar --baz and %quux the -4") == ['%quux']
assert RE_CMDLINE_OPTION.findall("-foo bar --baz and %quux the -4") == ['-foo', '--baz', '-4']

ESCAPE_DICT = {
    "t": "\t",
    "n": "\n",
    "\\": "\\",
    '"': '"',
}


Translation = collections.namedtuple("Translation", ["msgid", "msgstr", "line_first"])
Issue = collections.namedtuple("Issue", ["translation", "reason"])


def unescape(line: str) -> str:
    # Behold, the most inefficient but (hopefully) definitely-correct unescaper you have ever seen!
    parts = []
    is_quoted = False
    is_escaping = False
    for char in line:
        if is_escaping:
            is_escaping = False
            assert char in ESCAPE_DICT, "unknown escape sequence >>\\%s<<" % char
            parts.append(ESCAPE_DICT[char])
            continue
        if char == '"':
            is_quoted = not is_quoted
            continue
        assert is_quoted, "char %s not inside doublequotes; string is not properly escaped" % char
        if char == "\\":
            is_escaping = True
            continue
        parts.append(char)
    assert not is_quoted, "escaped string is not properly terminated"
    assert not is_escaping, "unfinished escape sequence; also, string not terminated"
    return "".join(parts)


# In-line unit test:
assert unescape('""') == ""
assert unescape('"asdf"') == "asdf"
assert unescape('"foo""bar"') == "foobar"
assert unescape('"Hello\\nWorld"') == "Hello\nWorld"
assert unescape('"Hello\\"World"') == 'Hello"World'
assert unescape('"fan\\\\cy"') == 'fan\\cy'


def parse_po_data(raw_data: str) -> List[Translation]:
    # None-ness indicates whether the start-tag has been seen already
    line_first: Optional[int] = None
    msgid_parts: Optional[List[str]] = None 
    msgstr_parts: Optional[List[str]] = None
    translations: List[Translation] = []
    i = -1
    for i, line in enumerate(raw_data.split("\n")):
        assert (line_first is None) == (msgid_parts is None), "line %d: inconsistent parser state" % (i + 1 - 1)
        if not line or line.startswith("#"):
            # Comment or empty line
            continue
        if msgid_parts is None:
            assert line.startswith("msgid "), "line %d: expected beginning of msgid" % (i + 1)
        if line.startswith("msgid "):
            assert (msgid_parts is None) == (msgstr_parts is None), "line %d: start of new translation, but previous from line %s is not complete?!" % (i + 1, line_first)
            if msgid_parts is not None:
                assert msgstr_parts is not None  # Otherwise, mypy does not understand that joining is okay.
                translations.append(Translation(
                    "".join(msgid_parts),
                    "".join(msgstr_parts),
                    line_first,
                ))
            line_first = i + 1
            msgid_parts = []
            msgstr_parts = None
            line = line[len("msgid "):]
            assert line.startswith('"'), "line %d: msgid does not directly continue with string?!" % (i + 1)
        if line.startswith("msgstr "):
            assert line_first is not None
            assert (msgid_parts is not None) and (msgstr_parts is None), "line %d: start of msgstr, but inconsistent state with line %d?!" % (i + 1, line_first)
            msgstr_parts = []
            line = line[len("msgstr "):]
        unescaped_line = unescape(line)
        if msgstr_parts is None:
            assert msgid_parts is not None
            msgid_parts.append(unescaped_line)
        else:
            msgstr_parts.append(unescaped_line)
    assert line_first is not None
    assert (msgid_parts is None) == (msgstr_parts is None), "line %d: end of file, but translation from line %d is not complete?!" % (i + 1, line_first)
    if msgid_parts is not None:
        assert msgstr_parts is not None  # Otherwise, mypy does not understand that joining is okay.
        translations.append(Translation(
            "".join(msgid_parts),
            "".join(msgstr_parts),
            line_first,
        ))
    return translations


def lint_translations(translations: List[Translation], lint_printf: bool) -> List[Issue]:
    issues: List[Issue] = []
    for t in translations:
        if not t.msgstr:
            # Don't complain about missing translations
            continue
        cmdline_msgid = RE_CMDLINE_OPTION.findall(t.msgid)
        cmdline_msgstr = RE_CMDLINE_OPTION.findall(t.msgstr)
        if lint_printf:
            printf_msgid = RE_PRINTFISH.findall(t.msgid)
            printf_msgstr = RE_PRINTFISH.findall(t.msgstr)
        else:
            printf_msgid = []
            printf_msgstr = []
        # TODO: Try harder to pin-point the specific difference
        if cmdline_msgid != cmdline_msgstr:
            issues.append(Issue(
                t,
                f"mismatching mentions of command-line options: >>{cmdline_msgid}<< (in msgid) versus >>{cmdline_msgstr}<< (in msgstr)",
            ))
        if printf_msgid != printf_msgstr:
            issues.append(Issue(
                t,
                f"mismatching printf instructions: >>{printf_msgid}<< (in msgid) versus >>{printf_msgstr}<< (in msgstr)",
            ))
    return issues


def run_on(openfile: Any, show_parsed_translations: bool, lint_printf: bool) -> None:
    # TODO: openfile is a TextIOWrapper. How to 'type' this correctly?
    raw_data: str = openfile.read()
    translations: List[Translation] = parse_po_data(raw_data)
    if show_parsed_translations:
        for t in translations:
            print(f"line {t.line_first}:")
            print(f"    {t.msgid}")
            print(f"    {t.msgstr}")
    translation_issues: List[Issue] = lint_translations(translations, lint_printf)
    for issue in translation_issues:
        # TODO: Aggregate across files?
        print(f"{openfile.name}:{issue.translation.line_first}: {issue.reason}")
        print(f"    msgid  = {issue.translation.msgid}")
        print(f"    msgstr  = {issue.translation.msgstr}")


def run(args: argparse.Namespace) -> None:
    for openfile in args.filenames:
        run_on(openfile, args.show_parsed_translations, args.lint_printf)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "Checks for grave translation errors and typos in command-line options or printf-style instructions."
    )
    parser.add_argument(
        "filenames",
        nargs="+",
        type=argparse.FileType("r", encoding="utf8"),
        help="Paths to the PO file(s)",
    )
    parser.add_argument(
        "--show-parsed-translations",
        action="store_true",
        help="Show all translations (useful to debug the parser)",
    )
    parser.add_argument(
        "--lint-printf",
        action="store_true",
        help="Show all translations (useful to debug the parser)",
    )
    return parser


if __name__ == "__main__":
    run(make_parser().parse_args())
