
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

* `-n`, `--new-rev`: Newer revision to compare with. If not given current HEAD of the Git repository will be used.
* `-d`, `--diff-name`: Name of the final diff file. '`PDF`' will be appended if necessary. Call `make-diff.py` with option `--help` to see its default.
* `-w`, `--overwrite`: If not given `make-diff.py` refuses to overwite an existing diff file.


### `flatten_latex.py`

Python module with a function to recusively resolve `\include` and `\input` directives. `make-diff.py` uses it for both revisions of the input file.

The module can also be called directly with the input file content provided on `stdin` while the result will be written to `stdout`.
