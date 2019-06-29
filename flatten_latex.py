#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Recursively replace LaTeX input and include commands by the respective files
#
# Can be used either as module providing the parseFile function or directly
# called with LaTeX code provided on stdin and the result written to stdout.


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
import re

# TODO: Currently \include is handled exactly like \input. Add and implement an option
#       to follow LaTeX specification to include only one level and obey \includeonly.


class Config():
	"""Configuration values"""

	# set to true to insert LaTeX comments to mark begin and end of inserted file
	addComments = True
	texExtension = ".tex"
	# regular expression to find input/include commands which are not commented out
	# the first part only allows '%' with an odd number of leading backslashes
	inputRe = re.compile("^(?P<before>(?:[^%\\\\]|\\\\.)*)\\\\(?:input|include)\{(?P<filename>.*?)\}(?P<after>.*)")


def parseFile(inFile, outFile):
	"""Copy inFile to outFile recursively inserting inputs

	inFile   readable text file object to parse
	outFile  writable text file object to write result into
	"""

	config = Config()

	def insertFile(fileName):
		"""Open file and copy and parse its content"""
		if config.addComments:
			outFile.write("% ========= begin insertion of " + fileName + " ==========\n")
		with open(fileName) as file:
			parseFile(file, outFile)
		if config.addComments:
			outFile.write("% ========= end insertion of " + fileName + " ==========\n")

	for line in inFile:
		# look for input command
		match = config.inputRe.search(line)
		if match:
			# part of the line before input command
			before = match.group('before')
			# argument of input command
			incFileName = match.group('filename').strip()
			# argument has not the right extension?
			if not incFileName.endswith(config.texExtension):
				incFileName += config.texExtension
			# part of the line after input command
			after = match.group('after')

			# copy line to outFile with input command replaced by input file's content
			outFile.write(before)
			insertFile(incFileName)
			outFile.write(after)
		else:
			# copy line to outFile
			outFile.write(line)


if __name__ == "__main__":
	inFile = sys.stdin
	outFile = sys.stdout
	parseFile(inFile, outFile)

