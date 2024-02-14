# lint-po-args

Checks for grave translation errors and typos, like translating "please use the -0 option" as "bitte nutze die -O Option", which is a different command-line option and likely won't work.

In particular, this script checks:
- Command-line flags
- (optionally) any printf-style format instructions

This little project was motivated by the following translation bug:

```
$ echo "oo'f" | xargs echo
xargs: Fehlendes korrespondierendes Anführungszeichen einfache; per Vorgabe sind Anführungszeichen für xargs bestimmt, sofern Sie nicht die Option -O verwenden
$ echo "oo'f" | LC_ALL=C xargs echo
xargs: unmatched single quote; by default quotes are special to xargs unless you use the -0 option
```

This project already finds real-life issues.

My goal is to make this some kind of successor in spirit to `POFileChecker`, which was [removed from Debian for using Python 2](https://tracker.debian.org/news/1091531/gettext-lint-removed-from-testing/). However, `lint-po-args` is not yet ready to be packaged.

## Table of Contents

- [Background](#background)
- [Usage](#usage)
- [TODOs](#todos)
- [TODONT](#todont)
- [Contribute](#contribute)

## Background

Command-line options usually are not translated. If some option is called `./foo --output`, then it is extremely unlikely that `./foo --ausgabe` does anything useful. Likewise, if some option is called `xargs -0` (with the digit zero), then suggesting `xargs -O` (with the capital letter o) is unlikely to be useful.

However, these errors absolutely happen: Sometimes a translator slips up, accidentally translates a keyword or a hardcoded option name, or misreads a `msgid` (the raw "original" message, often written in English), or a typo happens, or any number of other problems. That's fine, bugs happen.

Let's detect and fix these bugs!

The xargs example shows that this is a real-life usecase that hasn't been fixed for over a year. This tool tries to reveal all of them.

## Usage

Just call it with the path to your `.po` file, for example: `./lint_po_args.py de.po`

Full usage:

```
lint_po_args.py [-h] [--show-parsed-translations] [--lint-printf] filenames [filenames ...]

Checks for grave translation errors and typos in command-line options,
and optionally also printf-style instructions.

positional arguments:
  filenames
        Paths to the PO file(s)

options:
  -h, --help
        show this help message and exit
  --show-parsed-translations
        Show all translations (useful to debug the parser)
  --lint-printf
        Also check printf-style instructions
```

Note that plural support and any other "high-level" features are broken/missing, simply because I had to write my own PO-parser.

## TODOs

* Extend/replace the parser
* Does the regex need to be made more robust?
* Slightly more targeted hints would be nice, like a better diff on the list of detections (cmdlineargs/printf).
* Should the order matter? printf yes, cmdline maybe, interleaved … hard to say. Think more about that.
* Fix all the problems with translations everywhere. ;-)

## TODONT

* I don't aim to make this a replacement for `POFileChecker`. That said, if you find inspiration in it and extend this linter, I'd be happy to merge it!
* I'm not sure whether I even *want* this to be packaged, since this is such a highly-specialized lint. If you think about including this in Debian, please contact me, I'm sure we can work out something awesome :) 

## Contribute

Feel free to dive in! [Open an issue](https://github.com/BenWiederhake/lint-po-args/issues/new) or submit PRs.
