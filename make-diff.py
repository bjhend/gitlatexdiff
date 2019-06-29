#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Make a diff of a LaTeX file to another Git revision with latexdiff
#
# Call it with option --help for more info

# Copyright 2019 Björn Hendriks
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
import argparse
import os
import subprocess
import tempfile
import glob
import flatten_latex



def callCommand(args, cwd=None):
	'''Call args as shell command and return its stdout (NOT stderr)

	cwd  optional working directory
	'''
	result = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, check=True)
	return result.stdout.decode().strip()


class Configuration():
	'''Configuration values either from parsing command line or hard coded'''

	def __init__(self):
		args = self._parseArgs()

		## Hard coded config values
		# Options given to latexdiff
		self.latexdiffOptions = ['--append-textcmd=hint.*,todo']
		# Options given to pdflatex
		self.pdflatexOptions = ['-interaction=batchmode']
		# Number of successive calls of pdflatex to achieve the final result
		self.numTexRounds = 3
		self.latexExtension = '.tex'
		self.pdfExtension = '.pdf'

		## Values derived from command line or other sources
		self.mainFileAbs = self._makeAbsPathWithExtension(args.main, self.latexExtension)
		self.mainFileDir = os.path.dirname(self.mainFileAbs)
		self.diffNameAbs = self._makeAbsPathWithExtension(args.diff_name, self.pdfExtension)
		# Bail out if diffNameAbs exists and no --overwrite given
		if (not args.overwrite) and os.path.exists(self.diffNameAbs):
			sys.exit("Destination file " + self.diffNameAbs + " exists. Set --overwrite to overwrite it.")
		self.oldRevision = args.old_rev
		self.newRevision = args.new_rev
		self.initialDir = os.getcwd()

	def _makeAbsPathWithExtension(self, filename, extension):
		'''Return filename with absolute path and given extension if not already present'''
		pathname = os.path.abspath(filename)
		currRootname, currExt = os.path.splitext(pathname)
		return pathname if (currExt == extension) else (pathname + extension)

	def _parseArgs(self):
		'''Parse command line arguments'''
		parser = argparse.ArgumentParser(description='Make a LaTeX diff for two Git revisions of a LaTeX project')

		parser.add_argument('-m', '--main', required=True, help='Main LaTeX file (required)')
		parser.add_argument('-n', '--new-rev', default='HEAD', help='Ref to new revision to for diff (default: %(default)s)')
		parser.add_argument('-o', '--old-rev', required=True, help='Ref to old revision to for diff (required)')
		parser.add_argument('-d', '--diff-name', default='diff', help='Name for final diff file (default: %(default)s)')
		parser.add_argument('-w', '--overwrite', action='store_true', help='Silently overwrite existing diff (default: %(default)s)?')

		return parser.parse_args()

	def setNewRevisionIfHead(self, revision):
		'''If newRevision was HEAD (the default) replace it with revision'''
		if config.newRevision == 'HEAD':
			config.newRevision = revision



class GitRepo():
	'''Wrapper for all Git commands

	We do not apply GitPython or other third party packages to be as portable
	as possible. Instead we call the Git commands directly.
	'''

	def __init__(self, config):
		'''Find Git repo of main LaTeX file and check if it is clean'''
		self.repoDir = self._callGit(['rev-parse', '--show-toplevel'], config.mainFileDir)
		self.checkDirty()
		self.initialRevision = self.getCurrSymbolicRefOrHead()
		config.setNewRevisionIfHead(self.initialRevision)

	def getCurrSymbolicRefOrHead(self):
		'''Get HEAD as symbolic ref (branch name) if possible, otherwise its SHA1'''
		try:
			currSymbolicRev = self._callGit(['symbolic-ref', '--quiet', '--short', 'HEAD'])
		except subprocess.CalledProcessError:
			currSymbolicRev = self._callGit(['log', '-1', '--format=\'%H\''])
		return currSymbolicRev

	def checkDirty(self):
		'''Exit if repo contains uncommitted changes or files

		For details see
		stackoverflow.com/questions/2657935/checking-for-a-dirty-index-or-untracked-files-with-git#2659808
		'''
		try:
			self._callGit(['diff-index', '--quiet', 'HEAD', '--'])
		except subprocess.CalledProcessError:
			sys.exit("Uncommitted changes present. Commit or reset and try again.")

		untrackedFiles = self._callGit(['ls-files', '--exclude-standard', '--others'])
		if untrackedFiles:
			sys.exit("Untracked files present in " + self.repoDir + ":\n\n" + untrackedFiles + "\n\nAdd and commit or delete them and try again.")

	def checkout(self, revision):
		'''Check put given revision'''
		self._callGit(['checkout', revision])

	def reset(self):
		'''Reset to initial revision'''
		self.checkout(self.initialRevision)

	def _callGit(self, args, workingDir=None):
		'''Call a Git command in the repo or workingDir if given'''
		if workingDir is None:
			workingDir = self.repoDir
		return callCommand(['git'] + args, cwd=workingDir)



class Diff():
	'''Class to create the diff'''

	def __init__(self, config, gitRepo):
		'''Store config and repo'''
		self.config = config
		self.gitRepo = gitRepo

	def _makeTexFile(self, revision):
		'''Make a tex file from the main file in the given revision with resolved includes

		Return name of the new temporary file
		'''
		self.gitRepo.checkout(revision)
		with tempfile.NamedTemporaryFile(mode='w',
			                        suffix=self.config.latexExtension,
			                        dir=self.config.mainFileDir,
			                        delete=False) as texFile:
			with open(self.config.mainFileAbs) as mainFile:
				flatten_latex.parseFile(mainFile, texFile)
			return texFile.name

	def makeDiff(self):
		'''Create the diff PDF file in the directory this script was called from'''

		# TeX commands need to be executed in their repo to have correct access
		# to all temporary TeX files
		os.chdir(self.config.mainFileDir)

		# Make temp files with old and new version of flattened main file
		oldMainFilename = self._makeTexFile(self.config.oldRevision)
		newMainFilename = self._makeTexFile(self.config.newRevision)
		self.gitRepo.reset()

		# Make LaTeX diff
		diffTex = callCommand(['latexdiff'] + self.config.latexdiffOptions + [oldMainFilename, newMainFilename],
		                      cwd=self.config.mainFileDir)
		with tempfile.NamedTemporaryFile(mode='w',
			                        suffix=self.config.latexExtension,
			                        dir=self.config.mainFileDir,
			                        delete=False) as diffTexFile:
			diffTexFile.write(diffTex)
			diffTexFilename = diffTexFile.name

		# Call pdflatex sufficiently often on diff
		for i in range(self.config.numTexRounds):
			callCommand(['pdflatex'] + self.config.pdflatexOptions + [diffTexFilename], cwd=self.config.mainFileDir)

		# Move resulting PDF to initial dir
		diffPdfPathname = os.path.splitext(diffTexFilename)[0] + self.config.pdfExtension
		os.replace(diffPdfPathname, self.config.diffNameAbs)

		# Clean up temporaries
		os.remove(oldMainFilename)
		os.remove(newMainFilename)
		# Remove all temporary pdflatex files
		for temp in glob.iglob(os.path.splitext(diffTexFilename)[0] + '*'):
			os.remove(temp)


if __name__ == "__main__":
	config = Configuration()
	gitRepo = GitRepo(config)
	diff = Diff(config, gitRepo)
	diff.makeDiff()

