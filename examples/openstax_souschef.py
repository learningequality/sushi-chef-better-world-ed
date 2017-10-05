#!/usr/bin/env python

import os
import sys
sys.path.append(os.getcwd()) # Handle relative imports
from utils import data_writer, path_builder, downloader


""" Additional imports """
###########################################################
import logging
import json
import tempfile
from le_utils.constants import licenses, file_formats
from bs4 import BeautifulSoup
from selenium import webdriver

""" Run Constants"""
###########################################################

CHANNEL_NAME = "Example Open Stax"      # Name of channel
CHANNEL_SOURCE_ID = "souschef-example-learningequality" # Channel's unique id
CHANNEL_DOMAIN = "openstax.org"         # Who is providing the content
CHANNEL_LANGUAGE = "en"                 # Language of channel
CHANNEL_DESCRIPTION = None              # Description of the channel (optional)
CHANNEL_THUMBNAIL = "https://pbs.twimg.com/profile_images/461533721493897216/Q-kxGJ-b_400x400.png" # Local path or url to image file (optional)

PATH = path_builder.PathBuilder(channel_name=CHANNEL_NAME)          # Keeps track of path to write to csv
WRITE_TO_PATH = "{}{}{}.zip".format(os.path.dirname(os.path.realpath(__file__)), os.path.sep, CHANNEL_NAME) # Where to generate zip file

""" Additional Constants """
###########################################################

BASE_URL = "https://openstax.org/api"

# Map for Open Stax licenses to le_utils license constants
LICENSE_MAPPING = {
    "Creative Commons Attribution License": licenses.CC_BY,
    "Creative Commons Attribution-NonCommercial-ShareAlike License": licenses.CC_BY_NC_SA,
}
COPYRIGHT_HOLDER = "Rice University"

# Set up logging tools
LOGGER = logging.getLogger()
__logging_handler = logging.StreamHandler()
LOGGER.addHandler(__logging_handler)
LOGGER.setLevel(logging.INFO)


""" Main scraping method """
###########################################################
def scrape_source(writer):
    """ scrape_source: Scrapes channel page and writes to a DataWriter

        OpenStax is organized with the following hierarchy:
            Subject (Folder)
            |   Book (Folder)
            |   |   Main High Resolution PDF (File)
            |   |   Main Low Resolution PDF (File)
            |   |   Instructor Resources (Folder)
            |   |   |   Resource PDF (File)
            |   |   Student Resources (Folder)
            |   |   |   Resource PDF (File)

        Args: writer (DataWriter): class that writes data to folder/csv structure
        Returns: None
    """

    LOGGER.info("Parsing HTML from {}...".format(BASE_URL))

    contents = read_source()                                 # Get json data from page

    for book in contents.get('books'):
        PATH.set(book.get('subject'), book.get('title'))     # Start path at book level (Topic hierarchy: Subject -> Book)
        content = read_source(endpoint=book.get('slug'))     # Read detailed page for content

        if not content:                                      # Skip to next item if nothing is found
            continue

        # Format licensing metadata for content
        auth_info = {
            "license": LICENSE_MAPPING[content.get('license_name')],
            "license_description": content.get('license_text'),
            "copyright_holder": COPYRIGHT_HOLDER,
        }

        # Format content metadata for content
        authors = ", ".join([a['value']['name'] for a in content['authors'][:5]])
        authors = authors + " et. al." if len(content['authors']) > 5 else authors
        details = {
            "description": parse_description(content.get('description')),
            "thumbnail": get_thumbnail(content.get('cover_url')),
            "author": authors,
        }

        # Add book to topic tree
        writer.add_folder(str(PATH), book.get('title'), **details)

        # Read PDFs and write them using DataWriter tool
        LOGGER.info("   Writing {} documents...".format(book.get('title')))
        writer.add_file(str(PATH), "{} ({} Resolution)".format(content['title'], "High"), content.get("high_resolution_pdf_url"), **auth_info, **details)
        writer.add_file(str(PATH), "{} ({} Resolution)".format(content['title'], "Low"), content.get("low_resolution_pdf_url"),**auth_info, **details)
        writer.add_file(str(PATH), "Student Handbook", content.get("student_handbook_url"), **auth_info, **details)

        # Parse resource materials
        LOGGER.info("   Writing {} resources...".format(book.get('title')))
        parse_resources("Instructor Resources", content.get('book_faculty_resources'), writer, **auth_info)
        parse_resources("Student Resources", content.get('book_student_resources'), writer, **auth_info)


""" Helper Methods """
###########################################################

def read_source(endpoint="books"):
    """ Reads page source using downloader class to get json data """
    page_contents = downloader.read("{baseurl}/{endpoint}".format(baseurl=BASE_URL, endpoint=endpoint))
    return json.loads(page_contents) # Open Stax url returns json object

def get_thumbnail(url):
    """ Reads page source using downloader class to get json data """
    if url:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tempf:
            # Hacky method to get images, but much more lightweight than converting svg to png
            driver = webdriver.PhantomJS()
            driver.set_script_timeout(30)
            driver.get(url)
            driver.save_screenshot(tempf.name)
            tempf.close()
            thumbnail = writer.add_file(str(PATH), "thumbnail", tempf.name, write_data=False)
            os.unlink(tempf.name)
            return thumbnail

def parse_description(description):
    """ Removes html tags from description """
    return BeautifulSoup(description or "", "html5lib").text

def parse_resources(resource_name, resource_data, writer, **auth_info):
    """ Creates folders and files from resources """
    resource_data = resource_data or []
    PATH.open_folder(resource_name)       # Add resource to path (Topic hierarchy: Subject -> Book -> Resource)
    writer.add_folder(str(PATH), resource_name)
    for resource in resource_data:
        if resource.get('link_document_url'):
            _name, ext = os.path.splitext(resource['link_document_url'])
            if ext.lower() == ".pdf":
                title = resource.get('resource_heading')
                description = parse_description(resource.get('resource_description'))
                LOGGER.info("      Writing resource {}...".format(title))
                writer.add_file(str(PATH), title, resource.get("link_document_url"), description=description, **auth_info)

    PATH.go_to_parent_folder() # Go back one step in path (Topic hierarchy: Subject -> Book)


""" This code will run when the sushi chef is called from the command line. """
if __name__ == '__main__':

    # Open a writer to generate files
    with data_writer.DataWriter(write_to_path=WRITE_TO_PATH) as writer:

        # Write channel details to spreadsheet
        thumbnail = writer.add_file(str(PATH), "Channel Thumbnail", CHANNEL_THUMBNAIL, write_data=False)
        writer.add_channel(CHANNEL_NAME, CHANNEL_SOURCE_ID, CHANNEL_DOMAIN, CHANNEL_LANGUAGE, description=CHANNEL_DESCRIPTION, thumbnail=thumbnail)

        # Scrape source content
        scrape_source(writer)

        sys.stdout.write("\n\nDONE: Zip created at {}\n".format(writer.write_to_path))
