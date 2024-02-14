#!/usr/bin/env python3

"""
Checks for grave translation errors and typos, like translating "please use
the -0 option" as "bitte nutze die -O Option", which is a different symbol and
likely won't work.
In particular, this script checks:
- Command-line flags
- printf-style format instructions
See the regex for details.
"""

import collections
from typing import List, Optional
import re


FILENAME = "/scratch/findutils-deb/findutils-4.9.0/po/de_simplified.po"
SHOW_PARSED_TRANSLATIONS = False
ALSO_CHECK_PRINTF = False

if ALSO_CHECK_PRINTF:
    RE_SPECIAL_OPTION = re.compile(r"(?<![0-9a-zA-Z_-])-[0-9a-zA-Z_-]+|%[0-9a-zA-Z+-]+", re.M)
    # In-line unit test:
    assert RE_SPECIAL_OPTION.findall("-foo bar --baz and %quux the -4") == ['-foo', '--baz', '%quux', '-4']
else:
    RE_SPECIAL_OPTION = re.compile(r"(?<![0-9a-zA-Z_-])-[0-9a-zA-Z_-]+", re.M)
    # In-line unit test:
    assert RE_SPECIAL_OPTION.findall("-foo bar --baz and %quux the -4") == ['-foo', '--baz', '-4']

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
    if SHOW_PARSED_TRANSLATIONS:
        for t in translations:
            print(f"line {t.line_first}:")
            print(f"    {t.msgid}")
            print(f"    {t.msgstr}")
    return translations


def lint_translations(translations: List[Translation]) -> List[Issue]:
    issues: List[Issue] = []
    for t in translations:
        if not t.msgstr:
            # Don't complain about missing translations
            continue
        special_msgid = RE_SPECIAL_OPTION.findall(t.msgid)
        special_msgstr = RE_SPECIAL_OPTION.findall(t.msgstr)
        # TODO: Try harder to pin-point the specific difference
        if special_msgid != special_msgstr:
            issues.append(Issue(
                t,
                f"mismatching special-strings: >>{special_msgid}<< (in msgid) versus >>{special_msgstr}<< (in msgstr)",
            ))
    return issues


def run_on(filename: str) -> None:
    with open(filename, "r") as fp:
        raw_data: str = fp.read()
    po_data: List[Translation] = parse_po_data(raw_data)
    translation_issues: List[Issue] = lint_translations(po_data)
    for issue in translation_issues:
        # TODO: Aggregate across files?
        # TODO: Mention msgid somehow?
        print(f"{filename}:{issue.translation.line_first}: {issue.reason}")
        print(f"    msgid  = {issue.translation.msgid}")
        print(f"    msgstr  = {issue.translation.msgstr}")


if __name__ == "__main__":
    run_on(FILENAME)  # FIXME: Use argparse
