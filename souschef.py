#!/usr/bin/env python
import os
import sys
sys.path.append(os.getcwd()) # Handle relative imports
from utils import data_writer, path_builder, downloader
from le_utils.constants import licenses, exercises, content_kinds, file_formats, format_presets, languages


""" Additional imports """
###########################################################
import logging
import csv
import re		# Read hyperlinks and titles from csv file, hacky solution
import string 	# To work around forward slashes in titles, see additional notes (1)

""" Run Constants"""
###########################################################

CHANNEL_NAME = "Better World Ed"              # Name of channel
CHANNEL_SOURCE_ID = "learningequality"      # Channel's unique id
CHANNEL_DOMAIN = "info@learningequality.org"					# Who is providing the content
CHANNEL_LANGUAGE = "en"		# Language of channel
CHANNEL_DESCRIPTION = None                                  # Description of the channel (optional)
CHANNEL_THUMBNAIL = None                                    # Local path or url to image file (optional)
PATH = path_builder.PathBuilder(channel_name=CHANNEL_NAME)  # Keeps track of path to write to csv
WRITE_TO_PATH = "{}{}{}.zip".format(os.path.dirname(os.path.realpath(__file__)), os.path.sep, CHANNEL_NAME) # Where to generate zip file


""" Additional Constants """
###########################################################
BASE_URL = 'https://www.betterworlded.org/try'

# Read csv file

# csv file name
filename = "bwe_overall_database.csv"

# initializing titles and rows list
fields = []
rows = []

""" Main Scraping Method """
###########################################################
def scrape_source(writer):
	""" scrape_source: Scrapes channel page and writes to a DataWriter
        Args: writer (DataWriter): class that writes data to folder/spreadsheet structure
        Returns: None

        Better World Ed is organized with the following hierarchy:
            Grade Level (Folder) ***There may not be an assigned grade level*** (there should be 24 unassigned grade level rows)
            |   Math Topic (Folder)  ***May come as a hyperlink***
			|   |   Specific Objective (Folder) ***May come as a hyperlink***
			|   |   |   Written Story (File)
			|   |   |   Video (File)
			|   |   |   Lesson Plan (File)


		Additional notes:

		1)
		There are some cases where we would want to remove forward slashes (/), from the titles of files or folders.
		This is because when trying to name a folder, the PATH variable and Datawriter will create a new folder, for example:
		the 120th record, row 4, has the hyperlink, "I Am Shantanu // Chai & Community". This will cause the Datawriter to
		add a folder, "I Am Shantanu", with a file inside named " Chai & Community", with a preceding whitespace, instead
		of a file "I am Shantanu // Chai & Community".

		2)
		Take a look at record 294. Problems when trying to extract a pdf from google docs, vs google drive.

        Args: writer (Datawriter): class that writes data to folder/csv structure
		Returns: None
    """

	# To get the grade levels, go through the csv file and insert all
	# the grade levels into a set
	gradeLevels = set()
	count = 0 # Temporary, to verify correct output
	#docsRegex = re.search(r'https://docs\.google\.com/document/./([^/]*)', path)
	googleDocCount = 0


	with open(filename, 'r') as csvfile:
		# Creating csv reader object
		csvreader = csv.reader(csvfile)

		# Extracting each data row one by one
		for row in csvreader:
			#print ("loop")
			if count == 0: # Skip the headers
				count += 1
				continue
			if count == 2: # Temporary, to ensure code works on the first 5 rows
				break
				continue

			# Some folders are named as hyperlinks
			gradeLevel = row[0]
			if gradeLevel == "":
				gradeLevel = "Uncategorized"

			mathTopic = row[1]
			specificObjective = row[2]
			try:
				match = re.findall(r'\"(.+?)\"', row[1])
				#print ("Match: " + match[1])
				mathTopic = match[1].replace('/', '|')
			except:
				mathTopic = row[1].replace('/', '|')
			try:
				match = re.findall(r'\"(.+?)\"', row[2])
				specificObjective = match[1].replace('/', '|')
			except:
				specificObjective = row[2].replace('/', '|')

			PATH.set(gradeLevel, mathTopic, specificObjective)
			print ("PATH: " + str(PATH))


			writer.add_folder(str(PATH), specificObjective)

			# TODO: Search for 'Coming soon', and insert a try/except to see if
			#		the strings can be matched or not. If not, continue.

			# Written story (3th column, zero indexed)
			try:
				matches = re.findall(r'\"(.+?)\"', row[3])
				print ("Adding written story: " + matches[1])
				#title = remove_forward_slashes(matches[1])
				title = matches[1].replace('/', '|')
				print ("Adding written story: " + matches[1])
				#writer.add_file(str(PATH), title, matches[0], ext=".pdf", license=licenses.CC_BY, copyright_holder="betterworlded")
				writer.add_file(str(PATH), title, "https://docs.google.com/document/d/1s-5q5TfAj_OeiQjHzDL0a90q0NO_gEq9eZnF8TkeLdU/edit?usp=sharing", ext=".pdf", license=licenses.CC_BY, copyright_holder="betterworlded")
				#else:
				#	print ("Unable to extract pdf from Google Doc")
				#	googleDocCount += 1
			except Exception as e:
				print ("Error in extracting link from: " + row[3], str(e))


			# Video (4th column, zero indexed)
			try:
				matches = re.findall(r'\"(.+?)\"', row[4])
				title = matches[1].replace('/', '|')
				title = "I Am Shantanu // Chai & Community".replace('/', '|')
				print ("Adding video: " + title)
				print ("Video url: " + matches[0])
				file_path = writer.add_file(str(PATH), title, matches[0], ext=".mp4", license=licenses.CC_BY, copyright_holder="betterworlded")

			except:
				print ("Error in extracting link from: " + row[4])


			# Lesson plan (5th column, zero indexed)
			try:
				matches = re.findall(r'\"(.+?)\"', row[5])
				#title = remove_forward_slashes(matches[1])
				title = matches[1].replace('/', '|')
				print ("Adding lesson plan: " + matches[1])
				#if not "docs.google.com" in matches[0]:
				writer.add_file(str(PATH), str(matches[1]), matches[0], ext=".pdf", license=licenses.CC_BY, copyright_holder="betterworlded")
				#else:
				#	print ("Unable to extract pdf from Google Doc")
				#	googleDocCount += 1
			except:
				print ("Error in extracting link from: " + row[5])

			count += 1

	# TODO: Replace line with scraping code
	# raise NotImplementedError("Scraping method not implemented")

""" Helper Methods """
###########################################################


""" This code will run when the sous chef is called from the command line. """
if __name__ == '__main__':

    # Open a writer to generate files
    with data_writer.DataWriter(write_to_path=WRITE_TO_PATH) as writer:

        # Write channel details to spreadsheet
        thumbnail = writer.add_file(str(PATH), "Channel Thumbnail", CHANNEL_THUMBNAIL, write_data=False)
        writer.add_channel(CHANNEL_NAME, CHANNEL_SOURCE_ID, CHANNEL_DOMAIN, CHANNEL_LANGUAGE, description=CHANNEL_DESCRIPTION, thumbnail=thumbnail)

        # Scrape source content
        scrape_source(writer)

        sys.stdout.write("\n\nDONE: Zip created at {}\n".format(writer.write_to_path))
