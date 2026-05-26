
# Changelog

## 0.5.0 -- 2026-05-26

* Fix: site-name of docs does not follow renaming
* Extract flatten_latex to its own package [latex-include](https://pypi.org/project/latex-include/)
* Don't export the internal `main` function
* Many documentation improvements
* Catch missing executable and provide meaningful error message
* Catch non-existing main file or Git repo
* Catch non-existing revisions


## 0.4.0 -- 2026-05-23

* Add option `--version`
* Fix: documentation build broken due to renaming
* Made documentation available on Read the Docs


## 0.3.0 -- 2026-05-22

* Rename project to gitlatexdiff-original to avoid name clash on PyPI
* Add MkDocs configuration and improve documentation


## 0.2.0 -- 2026-05-17

* Refactoring to modern Python standards
* Bug fixes
* Enable comparison with current work files instead of enforcing to commit everything
* Make flatten directly callable
* Use Git worktrees to separate checkouts from original repo and for proper cleanup
* Add options for old main file and number of rounds
* Make flattening of \include command according to LaTeX standard
* Add type checking


## 0.1.0 -- 2020-01-29

Initial version
