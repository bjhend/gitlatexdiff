# Git-LaTeX-Diff Original

Make a rendered diff of two versions of a LaTeX document.


### License

See [License](LICENSE.md)


### Changelog

See [Changelog](CHANGELOG.md)


## Purpose

[*latexdiff*](https://www.ctan.org/pkg/latexdiff) is a LaTeX tool to create a diff of two LaTeX documents, which shows deletions and additions as red strike-through text and additions as blue underlined text when compiled to PDF. However, *latexdiff* has some major limitations.

To overcome the limitations, this Python script extends *latexdiff* in several ways:

* It works with a Git repo such that it compares the current state or a given commit with an earlier commit
* It resolves `\include` and `\input` commands like LaTeX does
* It calls `pdflatex` to render the final PDF

In addition the `\include` and `\input` resolving itself can be called as standalone script.



## Caveats

* While `\include` and `\input` are resolved from the respective git revisions, other includes like figures are resolved when compiling the diff. This is done in the new revision. So if the old version includes figures that are missing or renamed in the new revision they will be missing in the diff PDF as well.
* There is no diff of the bibliography and other generated parts.
* When using uncommitted changes as new version the rendering has to take place in the documents work directory. This may leave temporary files and have other unexpected side effects. However, if everything is committed or dedicated Git revisions are compared all processing is done in temporary directories that are cleaned up.



### Prerequesites

* LaTeX must be installed including the tools
    * `pdflatex`
    * `latexdiff`
* Python3 is available with at least the version set in `pyproject.toml`



## Usage

The easiest way is to apply the Python tool `uv`, which we describe here. Likely `poetry` will work as well.

Change to the directory where you cloned the gitlatexdiff project and call

```bash
uv sync
```

to install all dependencies and create a virtual environment.

To run the script call

```bash
uv run gitlatexdiff <options>
```

To run the script to flatten a LeTeX file standalone call

```bash
uv run flattenlatex <options>
```


#### Tips

If the diff sources cannot be compiled check the log file for problems with `\DIF...` commands and see which original LaTeX command caused it. Then you may exclude that command from the diff with for example:

`-l 'append-textcmd=hint.*,todo' 'exclude-textcmd=title,.*section,chapter'`

Here, LaTeX commands `\title`, `\chapter`, and all ending in `section` are excluded, so diffs in these commands are not marked in the output.

Note, that in this case the `'append-textcmd=hint.*,todo'` is the default for option `-l`, which needs to be set explicitely if `-l` is given.


### Options

Call `gitlatexdiff` with option `--help` to get the current list of command line options and their defaults if applicable.

#### Mandatory options

* `-m`, `--main`: Name of the main LaTeX file whose versions should be compared. It has to reside in the respective Git repository containing the versions to compare. May be given with path if `gitlatexdiff` is called from outside the LaTeX project directory.

#### Optional

All other command line options are optional.

Call `gitlatexdiff --help` to see the defaults of the following options.

* `-n`, `--new-rev`: Newer revision to compare with. If not given the current state of the work files is used, which will be the HEAD revision if all files are committed or else the work files.
* `-o`, `--old-rev`: Older revision to compare with. If not given either the revision before `--new-rev` is used or the HEAD revision if `--new-rev` is also not given and there are uncommitted changes.
* `--old-main`: Name of the old main LaTeX file which should be compared. Defaults to `--main`.
* `-d`, `--diff-name`: Name of the final diff file. '`.pdf`' will be appended if necessary. The log file of the last `pdflatex` call will be stored beside this file.
* `-w`, `--overwrite`: If not given `gitlatexdiff` refuses to overwite an existing diff file.
* `--num-rounds`: Number of calls to `pdflatex` when compiling the diff.

The following options are passed to `latexdiff` or `pdflatex` respectively. For technical reasons values have to be given without leading dashes. Dashes are prepended as required by the respective command.

* `-l`, `--latexdiff-options`: Arbitrary number of options passed to `latexdiff` call. Pass without any value to turn off the default.
* `-p`, `--pdflatex-options`: Arbitrary number of options passed to `pdflatex` call. Pass without any value to turn off the default.


### `flattenlatex`

Python module to recusively resolve `\include` and `\input` commands in a LaTeX document. `gitlatexdiff` uses it on both versions of the input file.

Call `uv run flattenlatex --help` to see its options to set input and output file. The input file is mandatory, because included files are drawn from its directory. The output file is optional, if omitted, `stdout` will be used.



## Documentation

Documentation is created with [MkDocs](https://www.mkdocs.org).

The following commands called from the base directory create the documentation:

* `uv run mkdocs serve` - Start the docs server.
* `uv run mkdocs build` - Build static documentation in subfolder `site/`
* `uv run mkdocs --help` - Print help message and exit.



## Contributing

Create issues or a pull requests to point out bugs or improvements.


## A note on the name

This project is called *Git-LaTeX-Diff Original* or `gitlatexdiff-original`, because the project name *gitlatexdiff* is already in use on [PyPI](https://pypi.org) for a similar [package](https://pypi.org/project/gitlatexdiff/) that was independently developed. It is called *original* due to the fact that the first publication of this project on GitHub is older.

