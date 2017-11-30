import requests
import time
import youtube_dl
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import tempfile
import subprocess
from selenium import webdriver
from requests_file import FileAdapter
from ricecooker.utils.caching import CacheForeverHeuristic, FileCache, CacheControlAdapter, InvalidatingCacheControlAdapter

DOWNLOAD_SESSION = requests.Session()                          # Session for downloading content from urls
DOWNLOAD_SESSION.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
DOWNLOAD_SESSION.mount('file://', FileAdapter())
cache = FileCache('.webcache')
forever_adapter= CacheControlAdapter(heuristic=CacheForeverHeuristic(), cache=cache)

DOWNLOAD_SESSION.mount('http://', forever_adapter)
DOWNLOAD_SESSION.mount('https://', forever_adapter)

# PyDrive
GAUTH = GoogleAuth()

GAUTH.LoadCredentialsFile("mycreds.txt")
if GAUTH.credentials is None:
    # Authenticate if they're not there
    GAUTH.LocalWebserverAuth()
elif GAUTH.access_token_expired:
    # Refresh them if expired
    GAUTH.Refresh()
else:
    # Initialize the saved creds
    GAUTH.Authorize()
# Save the current credentials to a file
GAUTH.SaveCredentialsFile("mycreds.txt")

# Create local webserver which automatically handles authentication
GAUTH.CommandLineAuth()

# Create Google Drive instance with authenticated GoogleAuth instance
DRIVE = GoogleDrive(GAUTH)


def read(path, loadjs=False):
    """ read: Reads from source and returns contents
        Args:
            path: (str) url or local path to download
            loadjs: (boolean) indicates whether to load js (optional)
        Returns: str content from file or page
    """

    try:
        # Look for the id from a google drive link or google docs link
        googleRegex = re.search(r'https://(?:drive|docs)\.google\.com/(?:document/./|file/./|open\?id=)([^/]*)', path)

        if googleRegex:
            with tempfile.NamedTemporaryFile(suffix='.pdf') as tempf:
                tempf.close()
                file_obj = DRIVE.CreateFile({'id': googleRegex.group(1)})
                file_obj.GetContentFile(tempf.name, mimetype='application/pdf')

                with open (tempf.name, "rb") as tf:
                    return tf.read()

        # If downloading a video from vimeo.com
        if "vimeo.com" in path:
            dlSettings = {"format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"}
            with tempfile.NamedTemporaryFile(suffix='.mp4') as tempf:
                dlSettings["outtmpl"] = tempf.name

                command = ['youtube-dl', path, "--no-check-certificate", "-o", tempf.name]

                tempf.close()

                subprocess.call(command)

                with open (tempf.name, "rb") as tf:
                    return tf.read()

        if loadjs:                                              # Wait until js loads then return contents
            driver = webdriver.PhantomJS()
            driver.get(path)
            time.sleep(5)
            return driver.page_source
        else:                                                   # Read page contents from url
            response = DOWNLOAD_SESSION.get(path, stream=True)
            response.raise_for_status()
            return response.content
    except (requests.exceptions.MissingSchema, requests.exceptions.InvalidSchema):
        with open(path, 'rb') as fobj:                          # If path is a local file path, try to open the file
            return fobj.read()
