
# Git-LaTeX-Diff

Apply `latexdiff` to a Git repository containing a LaTeX project.


## Purpose

[`latexdiff`](https://www.ctan.org/pkg/latexdiff) is a LaTeX tool to render a PDF file showing the differences between two LaTeX files. This script applies `latexdiff` on two revisions of a LaTeX file in a Git repository. Before that, it applies another script to recursively resolve `\include` and `\input` directives in the LaTeX code, because `latexdiff` does not consider those.


## Contact

For questions, remarks, etc. contact me via my Github account `bjhend`.


## Usage

1. Make sure the following prerequesites are fulfilled
1. Call `make-diff.py` (see below)

### Prerequesites

* LaTeX must be installed including the tools
    * `pdflatex`
    * `latexdiff`
* Python3 is available


## Scripts

### `make-diff.py`

The Python script to actually create the rendered diff.

#### Options

Call `make-diff.py` with option `--help` to get the current list of command line options and their defaults if applicable.

##### Mandatory

* `-m`, `--main`: Name of the main LaTeX file whose revisions should be compared. It has to reside in the respective Git repository containing the revisions to diff. May be given with path if `make-diff.py` is called from outside.
* `-o`, `--old-rev`: Reference of the old revision to compare with. Could be given in any form accepted by `git checkout`, for example as branch name, SHA1 or tag name.

##### Optional

Call `make-diff.py --help` to see the defaults of the following options.

* `-n`, `--new-rev`: Newer revision to compare with. If not given current HEAD of the Git repository will be used.
* `-d`, `--diff-name`: Name of the final diff file. '`PDF`' will be appended if necessary. If not path is given it will be put in the current directory. The log file of the last `pdflatex` call will be stored beside this file.
* `-w`, `--overwrite`: If not given `make-diff.py` refuses to overwite an existing diff file.

For technical reasons values to the following options have to be given without leading dashes. Dashes are prepended as required by the respective commands.

* `-l`, `--latexdiff-options`: Arbitrary number of options passed to `latexdiff` call. Pass without any value to turn off default.
* `-p`, `--pdflatex-options`: Arbitrary number of options passed to `pdflatex` call. Pass without any value to turn off default.

#### Tips

If the diff sources cannot be compiled check the log file for problems with `\DIF...` commands and see which original LaTeX command caused it. Then you may exclude that command from the diff with for example:

`-l 'append-textcmd=hint.*,todo' 'exclude-textcmd=title,.*section,chapter'`

Here, LaTeX commands `\title`, `\chapter`, and all ending in `section` are excluded, so diffs in these commands are not marked in the output.

Note, that in this case the `'append-textcmd=hint.*,todo'` is the default for option `-l`, which needs to be set explicitely if `-l` is given.


### `flatten_latex.py`

Python module with a function to recusively resolve `\include` and `\input` directives. `make-diff.py` uses it for both revisions of the input file.

The module can also be called directly with the input file content provided on `stdin` while the result will be written to `stdout`.
