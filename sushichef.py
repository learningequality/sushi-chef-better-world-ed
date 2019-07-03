#!/usr/bin/env python
import io
import os
import pandas as pd
import random
import re
import string
import youtube_dl
from googleapiclient.http import MediaIoBaseDownload

from le_utils.constants import licenses, languages
from ricecooker.chefs import SushiChef
from ricecooker.classes import nodes, files
from ricecooker.classes.licenses import get_license
from ricecooker.config import LOGGER
from ricecooker.exceptions import raise_for_invalid_channel

from extract import get_service



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
CHANNEL_THUMBNAIL = "chefdata/channel_thumbnail.jpg"



BWE_CSV_SAVE_DIR = 'chefdata'
BWE_CSV_SAVE_FILENAME = 'Better_World_Ed_Content_shared_for_Kolibri.csv'
# COL = ["Grade Level Range", "Math Topic", "Specific Objective",
#        "Written Story", "Video", "Lesson Plan", "BWE Topic"]

COL = ["Video", "Written Story", "Lesson Plan"]
GRADE_DICT = {}
DOWNLOAD_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "downloads")
CHANNEL_LICENSE = get_license(licenses.SPECIAL_PERMISSIONS, copyright_holder='Better World Ed', description='Sharing of select materials on Kolibri')



# Create download directory if it doesn't already exist
if not os.path.exists(DOWNLOAD_DIRECTORY):
    os.makedirs(DOWNLOAD_DIRECTORY)


# The chef subclass
################################################################################
class BetterWorldEdChef(SushiChef):
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
    video_file = files.VideoFile(
        path=video_path,
        language=languages.getlang('en').code,
        ffmpeg_settings={'crf': 30},
    )
    unique_id = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(5))
    LOGGER.info("\tCreating a video node - {}".format(video_title))
    video_node = nodes.VideoNode(
        source_id="{}-video-{}".format(video_source_id, unique_id),
        title=video_title,
        files=[video_file],
        license=CHANNEL_LICENSE,
        derive_thumbnail=True,
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
    drive = get_service(service_name='drive', service_version='v3')

    # Depends on the link type, grep the id(0B9q-Bz2y-5bySDBvYmh1N0abcde) part from document,
    # and download the pdf from the link for creating DocumentNodes
    if document_link.startswith("https://www.google.com/url?q=https"):
        info = document_link.split("/")[8]
        result = create_pdf(drive, info)
        if not result:
            return None
    elif "docs.google.com" in document_link:
        # if "a/reweave.org" in document_link:
        #     info = document_link.split("/")[7]
        #     result = create_pdf(drive, info, method='export')
        #     if not result:
        #         return None
        if "document/d" in document_link:
            info = document_link.split("/")[5]
            result = create_pdf(drive, info, method='export')
            if not result:
                return None
    elif "drive.google.com" in document_link:
        if "open?id=" in document_link:
            # print(document_link)
            info = document_link.split("open?id=")[1]
            result = create_pdf(drive, info, method='download')
            if not result:
                return None
        # elif "reweave.org/file/d" in document_link:
        #     info = document_link.split("/")[7]
        #     result = create_pdf(drive, info, method='download')
        #     if not result:
        #         return None
        elif "file/d/" in document_link:
            info = document_link.split("/")[5]
            result = create_pdf(drive, info, method='download')
            if not result:
                return None
        # elif "file/u/1/d" in document_link:
        #     info = document_link.split("/")[7]
        #     result = create_pdf(drive, info)
        #     if not result:
        #         return None
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

def create_pdf(drive, info, method):
    """
    Creates pdf in local directory.
    Skips if file already exists
    """
    assert method in ['download', 'export']
    # print('in create_pdf; info=', info)
    dest_path = './downloads/{}.pdf'.format(info)
    if not os.path.exists(dest_path):
        if method == 'download':
            # Google drive link
            request = drive.files().get_media(fileId=info)
        elif method == 'export':
            # Google docs link
            request = drive.files().export(fileId=info, mimeType='application/pdf')
        else:
            raise ValueError('unknown method', method)
        try:
            LOGGER.info("\tDownloading pdf file - {}.pdf".format(info))
            fh = io.FileIO(dest_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print("Downloading %d%%." % int(status.progress() * 100))
        except Exception as e:
            LOGGER.info("\n\n\tThere was an error while downloding {}".format(info))
            print(e)
            return None
    return info

def scrape_spreadsheet():
    """
    Create a DataFrame from csv file
    Sort them by grade to put `Others` in the last
    Scrape each row and structure a dictionary(GRADE_DICT) to represent the tree
    """
    content = pd.read_csv(os.path.join(BWE_CSV_SAVE_DIR,BWE_CSV_SAVE_FILENAME), usecols=COL, names=COL)
    # sorted_by_grade = content.sort_values(by="Grade Level Range", na_position="last")
    sorted_by_grade = content.sort_values(by="Video", na_position="last")

    for i, tup in enumerate(sorted_by_grade.iterrows()):
        _, row = tup

        # TMP HACKS since structure info is not available in current sheet
        grade = "Grade" #  if pd.isnull(row[0]) else row[0].strip()
        math_topic = 'Topic' # get_info(row[1])
        specific_obj = 'Learning objective ' + str(i+1) # get_info(row[2])
        # /TMP HACKS

        video_node = download_video(row[0])
        written_story = download_document(row[1])
        if written_story is None:
            print('failed to download written_story', row[1])
        lesson_plan = download_document(row[2])
        if lesson_plan is None:
            print('failed to download lesson_plan', row[2])
        
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
    chef = BetterWorldEdChef()
    chef.main()
