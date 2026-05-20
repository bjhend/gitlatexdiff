#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Make a diff of a LaTeX file to another Git revision with latexdiff
#
# Call it with option --help for more info

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



import os
import argparse
import subprocess
import tempfile
import pathlib as pl
import contextlib
import typing
from collections.abc import Generator
import shutil
from icecream import ic
from . import flatten_latex


latexExtension = '.tex'
pdfExtension = '.pdf'
logExtension = '.log'
messagePrefix = "------ "

# Command line option defaults
defaultNumRounds = 3
defaultDiffName = 'diff'
defaultLatexdiffOptions = ['append-textcmd=hint.*,todo']
defaultPdflatexOptions = ['interaction=batchmode']


def callCommand(args:list[str], cwd:pl.Path|None=None) -> str:
    """Call args as shell command and return its stdout (NOT stderr)

    Args:
        cwd: optional working directory

    Raises:
        subprocess.CalledProcessError: if the command returns with non-zero
                                       exit code

    Returns:
        stdout of the command
    """
    result = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, check=True)
    return result.stdout.decode().strip()


class Configuration():
    """Configuration values either from parsing command line or hard coded"""

    def __init__(self):
        """Get and preprocess command line arguments"""
        args = self._parseArgs()

        # Options given to latexdiff
        self.latexdiffOptions = self._prependPrefix('--', args.latexdiff_options)
        # Options given to pdflatex
        self.pdflatexOptions = self._prependPrefix('-', args.pdflatex_options)
        # Number of successive calls of pdflatex to achieve the final result
        self.numTexRounds = args.num_rounds
        if self.numTexRounds < 1:
            print(f"--num-rounds set to {self.numTexRounds}, but must be at least 1")
            exit(1)

        self.mainFileAbs = args.main.resolve().with_suffix(latexExtension)
        self.oldMainFileAbs = args.old_main.resolve().with_suffix(latexExtension) if args.old_main else self.mainFileAbs
        self.diffNameAbs = args.diff_name.resolve().with_suffix(pdfExtension)
        self.logNameAbs = args.diff_name.resolve().with_suffix(logExtension)

        # Bail out if diffNameAbs exists and no --overwrite given
        if (not args.overwrite) and self.diffNameAbs.exists():
            print(f"Destination file {self.diffNameAbs} exists. Delete it or set --overwrite to overwrite it.")
            exit(1)

        self.newRevision = args.new_rev
        self.oldRevision = args.old_rev

    def _prependPrefix(self, prefix:str, options:list[str]) -> list[str]:
        """Prepend prefix to all elements of options tuple

        Args:
            prefix:  string to prepend to all elements of options
            options: iterable of strings to prepend prefix to

        Returns:
            options with prefix prepended
        """
        return [ prefix + opt for opt in options ]

    def _parseArgs(self) -> argparse.Namespace:
        """Parse command line arguments

        Returns:
            result of argparse.ArgumentParser.parse_args()
        """
        parser = argparse.ArgumentParser(description='Make a LaTeX diff for two Git revisions of a LaTeX project')

        parser.add_argument('-m', '--main', type=pl.Path, required=True, help='Main LaTeX file (required)')
        parser.add_argument('-n', '--new-rev', help='Ref to new revision for diff (default: current state of the repo)')
        parser.add_argument('-o', '--old-rev', help='Ref to old revision for diff (default depends on --new-rev: If --new-rev is given'
                                                    ' one revision before --new-rev. If --new-rev is omitted but everything is committed'
                                                    ' then one before HEAD. Else HEAD itself.)')
        parser.add_argument('--old-main', type=pl.Path, help='Main LaTeX file of old revision (defaults to --main)')
        parser.add_argument('-d', '--diff-name', type=pl.Path, default=defaultDiffName, help='Name for final diff file (default: %(default)s)')
        parser.add_argument('-w', '--overwrite', action='store_true', help='Silently overwrite existing diff (default: %(default)s)')
        parser.add_argument('--num-rounds', type=int, default=defaultNumRounds, help='Number of pdflatexcalls to compile the diff (default: %(default)s)')
        parser.add_argument('-l', '--latexdiff-options', nargs='*', default=defaultLatexdiffOptions,
                            help='Options passed to latexdiff without leading dashes (default: %(default)s)')
        parser.add_argument('-p', '--pdflatex-options', nargs='*', default=defaultPdflatexOptions,
                            help='Options passed to pdflatex without leading dashes (default: %(default)s)')

        return parser.parse_args()


class GitRepo():
    """Wrapper for all Git commands

    We do not apply GitPython or other third party packages to be as portable
    as possible. Instead we call the Git commands directly.
    """

    def __init__(self, config:Configuration):
        """Init GitRepo with given config

        Args:
            config: configuration with main file path
        """
        self.repoDir = pl.Path(self._callGit(['rev-parse', '--show-toplevel'], config.mainFileAbs.parent))

    def getSha1(self, committish:str) -> str:
        """Return SHA1 of committish

        Args:
            committish: any string that Git recognizes as a commit reference: HEAD,
                        branch, tag, or their parents

        Returns:
            SHA1 of the referenced commit or `None` if it cannot be resolved
        """

        try:
            return self._callGit(['rev-parse', committish])
        except subprocess.CalledProcessError:
            return None

    def isDirty(self) -> bool:
        """Check if uncommitted changes or new non-ignored files are present

        Returns:
            `True` if there are uncommitted files
        """
        try:
            # Returns with non-zero exitcode if a committed file is altered
            self._callGit(['diff-index', '--quiet', 'HEAD', '--'])
        except subprocess.CalledProcessError:
            return True

        # Returns list of non-ignored untracked files
        untrackedFiles = self._callGit(['ls-files', '--exclude-standard', '--others'])
        return bool(untrackedFiles)

    @contextlib.contextmanager
    def worktree(self, sha1:str|None=None) -> Generator[pl.Path]:
        """Check out sha1 in a temporary worktree and finally cleanup or return repo dir

        This is a contextmanager, so call it in a `with` statement.

        If `sha1` is given check it out in a temporary worktree and remove the
        worktree on exit of the context. If `sha1` is `None` return the repo dir
        itself.

        Args:
            sha1: SHA1 of the commit to check out in the worktree, if `None` return
                  the repo dir itself

        Returns:
            path to the work files
        """

        if not sha1:
            yield self.repoDir
            return

        with tempfile.TemporaryDirectory(prefix='gitlatexdiff_worktree_') as workDir:
            workDirPath = pl.Path(workDir)
            self._callGit(['worktree', 'add', '--force', str(workDirPath), sha1])
            try:
                yield workDirPath
            finally:
                self._callGit(['worktree', 'remove', str(workDirPath)])

    def _callGit(self, args:list[str], workingDir:pl.Path|None=None) -> str:
        """Call a Git command in the repo or workingDir if given

        Prepends `git` to the given args and calls callCommand() with them.

        Args:
            args:       command line arguments for the Git command (without `git` itself)
            workingDir: optional dir to execute the command in, if ommitted use
                        the repo dir

        Return:
            stdout of the command

        Raises:
            see callCommand()
        """
        if workingDir is None:
            workingDir = self.repoDir
        return callCommand(['git'] + args, cwd=workingDir)



class Diff():
    """Class to create the diff"""

    def __init__(self, config:Configuration, gitRepo:GitRepo):
        """Init

        Args:
            config:  configuration
            gitRepo: Git repo
        """

        self.config = config
        self.gitRepo = gitRepo
        self.mainFileRelative = self.config.mainFileAbs.relative_to(self.gitRepo.repoDir)
        self.oldMainFileRelative = self.config.oldMainFileAbs.relative_to(self.gitRepo.repoDir)

        # Determine new sha1
        if config.newRevision:
            self.newSha1:str|None = self.gitRepo.getSha1(config.newRevision)
        else:
            if self.gitRepo.isDirty():
                self.newSha1 = None
            else:
                self.newSha1 = self.gitRepo.getSha1('HEAD')

        # Determine old sha1
        if config.oldRevision:
            self.oldSha1 = self.gitRepo.getSha1(config.oldRevision)
        else:
            if self.newSha1:
                # Use one revision before new sha1
                self.oldSha1 = self.gitRepo.getSha1(self.newSha1 + '~')
            else:
                # Compare work files with HEAD revision
                self.oldSha1 = self.gitRepo.getSha1('HEAD')

    @contextlib.contextmanager
    def _flatFile(self, sha1:str|None, mainFileRelative:pl.Path) -> Generator[pl.Path]:
        """Flatten mainFileRelative in the given sha1 revision and return its path

        This method is a contextmanager. So it needs to be called in a
        with-statement. On leaving the context the returned file and the worktree
        will be removed.

        Flatten resolves all include/input commands.

        If sha1 is not None flattening is done in an exclusive worktree to avoid
        interfering with the repo.

        Args:
            sha1:             revision to check out, if None use the repo itself
            mainFileRelative: relative path to the main file in the repo

        Returns:
            name of the temporary file
        """
        version = f"version {sha1}" if sha1 else "current version"
        print(f"{messagePrefix}Flattening {mainFileRelative} in {version}")
        with self.gitRepo.worktree(sha1) as workDir:
            mainFileDir = workDir / mainFileRelative.parent
            os.chdir(mainFileDir)
            with tempfile.NamedTemporaryFile(mode='w',
                                        prefix='flattened_',
                                        suffix=latexExtension,
                                        dir=mainFileDir,
                                        delete_on_close=False) as texFile:
                with (workDir / mainFileRelative).open() as mainFile:
                    flatten_latex.flatten(mainFile, typing.cast(typing.TextIO, texFile.file))
                texFile.close()
                yield pl.Path(texFile.name)

    def makeDiff(self) -> None:
        """Create the diff PDF file in the directory this script was called from"""

        # Make LaTeX diff
        with (self._flatFile(self.oldSha1, self.oldMainFileRelative) as oldFlatInput,
              self._flatFile(self.newSha1, self.mainFileRelative) as newFlatInput):
            print(f"{messagePrefix}Create diff")
            diffTex = callCommand(['latexdiff'] + self.config.latexdiffOptions
                                  + [str(oldFlatInput), str(newFlatInput)])

        # Compile diff in a worktree and move it to its configure final path.
        # Note that workDir is the repo itself if self.newSha1 is None.
        with self.gitRepo.worktree(self.newSha1) as workDir:
            mainFileDir = workDir / self.mainFileRelative.parent

            # TeX commands need to be executed in their repo to have correct access
            # to all temporary TeX files
            os.chdir(mainFileDir)

            with tempfile.NamedTemporaryFile(mode='w',
                                        prefix='diff_',
                                        suffix=latexExtension,
                                        dir=mainFileDir,
                                        delete_on_close=False) as diffTexFile:
                diffTexFile.write(diffTex)
                diffTexFile.close()
                diffTexFilePath = pl.Path(diffTexFile.name)

                # Call pdflatex sufficiently often on diff
                for i in range(self.config.numTexRounds):
                    print(f"{messagePrefix}Compiling diff round {i+1}")
                    try:
                        callCommand(['pdflatex'] + self.config.pdflatexOptions + [str(diffTexFilePath)], cwd=mainFileDir)
                    except subprocess.CalledProcessError as ex:
                        # Sometimes a pdfltex call returns an error but still works
                        print(f"Warning: pdflatex returned an error, which we ignore: {ex}")
                        print(f"See pdflatex log for possible causes: {self.config.logNameAbs}")

                # Move resulting PDF and log to initial dir
                diffPdfPathname = diffTexFilePath.with_suffix(pdfExtension)
                diffLogPathname = diffTexFilePath.with_suffix(logExtension)
                shutil.move(diffLogPathname, self.config.logNameAbs)
                try:
                    shutil.move(diffPdfPathname, self.config.diffNameAbs)
                except FileNotFoundError:
                    print(f"No diff created. See log files for possible cause: {self.config.logNameAbs}")
                    print("Hint: It may help exclude LaTeX commands with for example \"-l 'exclude-textcmd=title,.*section,chapter'\"")

        # Remove all temporary pdflatex files
        # This is only relevant if a diff with current dirty work files was made,
        # so it was compiled in the repo itself instead of a temp worktree.
        for path in diffTexFilePath.parent.glob(f'{diffTexFilePath.stem}*'):
            path.unlink()

        print(f"{messagePrefix}Successfully created diff {self.config.diffNameAbs}")


def main() -> None:
    """Entry point"""

    try:
        config = Configuration()
        gitRepo = GitRepo(config)
        diff = Diff(config, gitRepo)
        diff.makeDiff()
    except Exception as ex:
        print(f"An error occurred: {ex}")
        exit(1)


if __name__ == "__main__":
    main()

