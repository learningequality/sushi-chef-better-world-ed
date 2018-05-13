#!/usr/bin/env python
import os
import random
import re
import string
import youtube_dl
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from ricecooker.chefs import SushiChef
from ricecooker.classes import nodes, files, licenses
from ricecooker.config import LOGGER
from ricecooker.exceptions import raise_for_invalid_channel
from le_utils.constants import licenses, languages
import pandas as pd

CHANNEL_NAME = "Better World Ed"              # Name of channel
CHANNEL_SOURCE_ID = "sushi-chef-better-world-ed"    # Channel's unique id
CHANNEL_DOMAIN = "https://www.betterworlded.org"          # Who is providing the content
CHANNEL_LANGUAGE = "en"      # Language of channel
CHANNEL_DESCRIPTION = "K-12 curriculum aligned to various sets "\
                      "of standards designed to promote “STEMpathy,” "\
                      "a human-centered approach to teaching math and "\
                      "science. Videos, stories, and lesson plans to help "\
                      "teach empathy in the context of the regular math and "\
                      "literacy curriculum."
CHANNEL_THUMBNAIL = "thumbnail.jpg"

COL = ["Grade Level Range", "Math Topic", "Specific Objective",
       "Written Story", "Video", "Lesson Plan", "BWE Topic"]
GRADE_DICT = {}
DOWNLOAD_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "downloads")
CHANNEL_LICENSE = licenses.PUBLIC_DOMAIN


# Create download directory if it doesn't already exist
if not os.path.exists(DOWNLOAD_DIRECTORY):
    os.makedirs(DOWNLOAD_DIRECTORY)

# The chef subclass
################################################################################
class MyChef(SushiChef):
    """
    This class uploads the Better World Ed channel to Kolibri Studio.
    """
    channel_info = {                                   # Channel Metadata
        'CHANNEL_SOURCE_DOMAIN': CHANNEL_DOMAIN,       # Who is providing the content
        'CHANNEL_SOURCE_ID': CHANNEL_SOURCE_ID,        # Channel's unique id
        'CHANNEL_TITLE': CHANNEL_NAME,                 # Name of channel
        'CHANNEL_LANGUAGE': CHANNEL_LANGUAGE,          # Language of channel
        'CHANNEL_THUMBNAIL': CHANNEL_THUMBNAIL,        # Local path or url to image file (optional)
        'CHANNEL_DESCRIPTION': CHANNEL_DESCRIPTION,    # Description of the channel (optional)
    }

    def construct_channel(self, *args, **kwargs):
        """
        Creates ChannelNode and build topic tree
        Bettwe-World-Ed is organized with the following hierarchy:
        1st - 3rd (Topic)
        |--- Measurement and Data (Topic)
        |---|--- Measuring length (Topic)
        |---|---|--- Dayna on the art of hats (Pdf - DocumentNode)
        |---|---|--- I am dayna (Viedeo - VideoNode)
        |---|---|--- What is art (Pdf - DocumentNode)
        ...
        """
        channel = self.get_channel(*args, **kwargs)
        scrape_spreadsheet()
        for grade in GRADE_DICT:
            source_id = grade.strip().replace(" ", "_")
            LOGGER.info("\tCreating a topic node - {}".format(grade))
            topic = nodes.TopicNode(source_id=source_id, title=grade.capitalize())
            get_nodes_from_dict(topic, GRADE_DICT[grade], grade)
            channel.add_child(topic)
        raise_for_invalid_channel(channel)  # Check for errors in channel construction
        return channel

def get_nodes_from_dict(parent, dictionary, prefix):
    """
    Strucutre nodes from dictionary to connect them
    """
    for topic in dictionary:
        if isinstance(topic, str):
            topic_source_id = "{}-{}".format(prefix, topic.strip().replace(" ", "_"))
            topic_node = nodes.TopicNode(source_id=topic_source_id, title=topic.capitalize())
            LOGGER.info("\tCreating a math topic node - {}".format(topic))
            get_nodes_from_dict(topic_node, dictionary[topic], topic_source_id)
            parent.add_child(topic_node)
        else:
            for node in topic:
                if node and not isinstance(node, str):
                    LOGGER.info("\tAdding a child node - {}".format(node))
                    parent.add_child(node)


def get_info(information):
    """
    Retrieves title of the source
    For example, from the information below,
    HYPERLINK("https://drive.google.com/open?id=0B9q-Bz2y-5byRWZwRHptZmk0eU0","Baby And Her Health")
    Returns `Baby And Her Health`
    """
    information = information.lower()
    if information.startswith("=hyperlink"):
        splits = information.split(",")
        return splits[1].split("\"")[1].strip()
    return information.strip()

def download_video(link):
    """
    downloads video from the link
    and returns video node
    """
    if "=HYPERLINK" not in link:
        return link
    splits = link.split(",")
    video_link = splits[0].split("=HYPERLINK(\"")[1][:-1]
    video_id = video_link.split("/")[-1]
    ydl = youtube_dl.YoutubeDL({
        'outtmpl': './downloads/%(id)s.%(ext)s',
        'writeautomaticsub': True
    })

    with ydl:
        try:
            result = ydl.extract_info(video_link)
        except:
            LOGGER.info("\tThere was an error while downloding video - {}".format(video_link))
            return None

    if 'entries' in result:
        video = result['entries'][0]
    else:
        video = result

    video_title = video["title"].capitalize()
    video_source_id = video_title.strip().replace(" ", "_")
    video_path = "{}/{}.mp4".format(DOWNLOAD_DIRECTORY, video_id)
    video_file = files.VideoFile(path=video_path, language=languages.getlang('en').code)
    unique_id = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(5))
    LOGGER.info("\tCreating a video node - {}".format(video_title))
    video_node = nodes.VideoNode(
        source_id="{}-video-{}".format(video_source_id, unique_id),
        title=video_title,
        files=[video_file],
        license=CHANNEL_LICENSE
    )
    return video_node

def download_document(link):
    """
    Downloads pdf from the link
    and returns document node
    """

    # Return if link does not contain hyperlink information
    if "=HYPERLINK" not in link:
        return link

    # For example, if the link is - HYPERLINK("https://drive.google.com/open?id=0B9q-Bz2y-5bySDBvYmh1N0abcde","Test Document")
    # this method extracts document_link and document_title
    # https://drive.google.com/open?id=0B9q-Bz2y-5bySDBvYmh1N0abcde as document_link
    # Test Document as document_title
    splits = link.split("\",\"")
    document_title = re.search('(.*)\"\)', splits[1]).group(1)
    document_link = splits[0].split("=HYPERLINK(\"")[1]

    # Use GoogleAuth to download documents from links - e.g. googleDocs, googleDrive.
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    # Depends on the link type, grep the id(0B9q-Bz2y-5bySDBvYmh1N0abcde) part from document,
    # and download the pdf from the link for creating DocumentNodes
    if document_link.startswith("https://www.google.com/url?q=https"):
        info = document_link.split("/")[8]
        result = create_pdf(drive, info)
        if not result:
            return None
    elif "docs.google.com" in document_link:
        if "a/reweave.org" in document_link:
            info = document_link.split("/")[7]
            result = create_pdf(drive, info)
            if not result:
                return None
        elif "document/d" in document_link:
            info = document_link.split("/")[5]
            result = create_pdf(drive, info)
            if not result:
                return None
    elif "drive.google.com" in document_link:
        if "open?id=" in document_link:
            info = document_link.split("open?id=")[1]
            result = create_pdf(drive, info)
            if not result:
                return None
        elif "reweave.org/file/d" in document_link:
            info = document_link.split("/")[7]
            result = create_pdf(drive, info)
            if not result:
                return None
        elif "file/d/" in document_link:
            info = document_link.split("/")[5]
            result = create_pdf(drive, info)
            if not result:
                return None
        elif "file/u/1/d" in document_link:
            info = document_link.split("/")[7]
            result = create_pdf(drive, info)
            if not result:
                return None
    else:
        return None

    # Creating DocumentNode with downloaded information
    LOGGER.info("\tCreating a pdf node - {}".format(document_title))
    pdf_path = "{}/{}.pdf".format(DOWNLOAD_DIRECTORY, info)
    pdf_file = files.DocumentFile(pdf_path)
    unique_id = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(5))

    # Adding unique_id to eliminate possible conflicts with nodes with same source_id.
    pdf_source_id = "{}-{}".format(unique_id, info)
    pdf_node = nodes.DocumentNode(
        source_id=pdf_source_id,
        title=document_title.capitalize(),
        files=[pdf_file],
        license=CHANNEL_LICENSE
    )
    return pdf_node

def create_pdf(drive, info):
    """
    Creates pdf in local directory.
    Skips if file already exists
    """
    if not os.path.exists('./downloads/{}.pdf'.format(info)):
        file_obj = drive.CreateFile({'id': info})
        try:
            LOGGER.info("\tDownloading pdf file - {}.pdf".format(info))
            file_obj.GetContentFile('./downloads/{}.pdf'.format(info), mimetype="application/pdf")
        except:
            LOGGER.info("\tThere was an error while downloding {}".format(info))
            return None
    return info

def scrape_spreadsheet():
    """
    Create a DataFrame from csv file
    Sort them by grade to put `Others` in the last
    Scrape each row and structure a dictionary(GRADE_DICT) to represent the tree
    """
    content = pd.read_csv("bwe_overall_database.csv", usecols=COL, names=COL)
    sorted_by_grade = content.sort_values(by="Grade Level Range", na_position="last")

    for _, row in sorted_by_grade.iterrows():
        grade = "Other" if pd.isnull(row[0]) else row[0].strip()
        math_topic = get_info(row[1])
        specific_obj = get_info(row[2])
        written_story = download_document(row[3])
        video_node = download_video(row[4])
        lesson_plan = download_document(row[5])
        group = [written_story, video_node, lesson_plan]

        if grade not in GRADE_DICT:
            GRADE_DICT[grade] = {math_topic: {specific_obj: [group]}}
        else:
            if math_topic not in GRADE_DICT[grade]:
                GRADE_DICT[grade][math_topic] = {specific_obj: [group]}
            else:
                if specific_obj not in GRADE_DICT[grade][math_topic]:
                    GRADE_DICT[grade][math_topic][specific_obj] = [group]
                else:
                    GRADE_DICT[grade][math_topic][specific_obj].append(group)

# CLI
################################################################################
if __name__ == '__main__':
    # This code runs when sushichef.py is called from the command line
    chef = MyChef()
    chef.main()
