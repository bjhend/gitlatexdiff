#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Recursively replace LaTeX input and include commands by the respective files
#
# Can be used either as module providing the parseFile function or directly
# called with LaTeX code provided on stdin and the result written to stdout.


# Copyright 2019,2026 Björn Hendriks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys
import os
import re
import typing
import argparse
import pathlib as pl
import contextlib
from icecream import ic



class _Config():
    """Configuration values"""

    texExtension = '.tex'
    # regular expression to find input/include commands which are not commented out
    # the first part only allows '%' with an odd number of leading backslashes

    commandPattern = r"^(?P<before>(?:[^%\\]|\\.)*)\\{cmd}{{(?P<filename>.*?)}}(?P<after>.*)"
    inputRe = re.compile(commandPattern.format(cmd='input'))
    includeRe = re.compile(commandPattern.format(cmd='include'))
    includeOnlyRe = re.compile(commandPattern.format(cmd='includeonly'))


def flattenRecursion(inFile:typing.TextIO, outFile:typing.TextIO,
                     includeOnly:list[str]|None=None, isResolveInclude:bool=True) -> None:
    """Copy inFile to outFile recursively inserting inputs and includes

    According to LaTeX \input is always inserted but \include is more special.
    \include cannot be nested and if \includeonly is given in the preamble
    includes are limited to those files. In addition \include is surrounded by
    \clearpage.

    inFile:           readable text file object to parse
    outFile:          writable text file object to write result into
    includeOnly:      list of filenames to include found in \includeonly command
    isResolveInclude: True if \include should be resolved to avoid nested inclusion
    """
    config = _Config()

    def getFilename(match:re.Match) -> str:
        """Get filename argument from command match"""
        return match.group('filename').strip()

    def insertFile(match:re.Match, isInclude:bool) -> None:
        """Open filename in match and insert its content"""

        if isInclude:
            label = 'include'
            surround = "\\clearpage  % inserted due to resolved include\n"
            newIsResolveInclude = False
        else:
            label = 'input'
            surround = ''
            newIsResolveInclude = isResolveInclude

        fileName = getFilename(match)
        if not fileName.endswith(config.texExtension):
            fileName += config.texExtension
        before = match.group('before')
        after = match.group('after')

        outFile.write(before)
        outFile.write(f"% ========= begin {label} of {fileName} ==========\n")
        outFile.write(surround)
        with open(fileName) as file:
            flattenRecursion(file, outFile, includeOnly=includeOnly,
                             isResolveInclude=newIsResolveInclude)
        outFile.write(surround)
        outFile.write(f"% ========= end {label} of {fileName} ==========\n")
        outFile.write(after)

    for line in inFile:
        # Handle \includeonly
        matchIncludeOnly = config.includeOnlyRe.search(line)
        if matchIncludeOnly:
            filenames = getFilename(matchIncludeOnly).split(sep=',')
            includeOnly = [ f.strip() for f in filenames ]

        # Handle \input
        matchInput = config.inputRe.search(line)
        if matchInput:
            insertFile(match=matchInput, isInclude=False)
            continue

        # Handle \include
        if isResolveInclude:
            matchInclude = config.includeRe.search(line)
            if matchInclude:
                if (not includeOnly) or (getFilename(matchInclude) in includeOnly):
                    insertFile(match=matchInclude, isInclude=True)
                    continue

        # Copy line
        outFile.write(line)


def flatten(inFile:typing.TextIO, outFile:typing.TextIO) -> None:
    """Start recursively resolving includes"""
    flattenRecursion(inFile, outFile)


def flattenFiles(inPath:pl.Path, outPath:pl.Path|None=None) -> None:
    """Open files and call flatten() with them

    Both files can be given as pathlib.Path or string.

    We require inPath instead of defaulting to stdin, because we need
    its directory to resolve relative input/include paths in the LaTeX code

    inPath:  name of input file
    outPath: optional name of output file, if omitted stdout is used instead

    Raises OSError if a file cannot be opened.
    """
    cwd = pl.Path.cwd()
    try:
        inPath = pl.Path(inPath)
        assert inPath.is_file()

        inPathAbs = inPath.absolute()
        if outPath:
            outPath = pl.Path(outPath)
            output:contextlib.AbstractContextManager[typing.TextIO] = contextlib.closing(outPath.absolute().open('w'))
        else:
            output = contextlib.nullcontext(sys.stdout)

        # Change dir to resolve relative inputs/includes
        os.chdir(inPathAbs.parent)

        with inPathAbs.open() as inFile:
            with output as outFile:
                flatten(inFile, outFile)
    finally:
        os.chdir(cwd)


def flattenCommand() -> None:
    """Call flatten from command line

    Parses command line for input and output and calls flattenFiles with them.

    If output exists an additional command line flag is required to overwrite it.
    """
    parser = argparse.ArgumentParser(description="Flatten a LaTeX file to a single file with all input/include resolved")

    # See flattenFiles documentation, why --input is required
    parser.add_argument('-i', '--input', required=True, type=pl.Path, help="Main LaTeX file to flatten")
    parser.add_argument('-o', '--output', type=pl.Path, help="Output file, default is stdout")
    parser.add_argument('-w', '--overwrite', action='store_true', help="Silently overwrite existing diff? (default: %(default)s)")
    args = parser.parse_args()

    if args.output and (not args.overwrite) and args.output.exists():
        print(f"Output {args.output} exists. Delete it or set option --overwrite (-w) to overwrite it.")
        exit(1)

    try:
        flattenFiles(args.input, args.output)
    except OSError as ex:
        print(f"Cannot open input or output file: {ex}")
        exit(1)


if __name__ == "__main__":
    flattenCommand()

