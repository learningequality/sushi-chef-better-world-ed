#!/usr/bin/env python
import csv

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# Creds
CLIENT_SECRET_FILE = 'credentials/client_secret.json'  # server application -- this will request OAuth2 login
CLIENT_TOKEN_PICKLE = 'credentials/token.pickle'
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
]

# Source
BWE_SPREADSHEET_ID = '11WtfabcInVp7M7BW9Vdxi_ujSl-65z7yaTfeuU4sM5A'
BWE_SHEET_NAME = 'Sheet1'
BWE_RANDE = 'A3:C378'
BWE_EXTRACT_RANGE = BWE_SHEET_NAME + '!' + BWE_RANDE

# Destination
BWE_CSV_SAVE_DIR = 'chefdata'
BWE_CSV_SAVE_FILENAME = 'Better_World_Ed_Content_shared_for_Kolibri.csv'


class MemoryCache():
    # workaround for error "file_cache is unavailable when using oauth2client >= 4.0.0 or google-auth'"
    # via https://github.com/googleapis/google-api-python-client/issues/325#issuecomment-274349841
    _CACHE = {}

    def get(self, url):
        return MemoryCache._CACHE.get(url)

    def set(self, url, content):
        MemoryCache._CACHE[url] = content



def get_service(service_name='sheets', service_version='v4'):
    # https://developers.google.com/sheets/api/quickstart/python#step_3_set_up_the_sample
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(CLIENT_TOKEN_PICKLE):
        with open(CLIENT_TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open(CLIENT_TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)

    service = build(service_name, service_version, credentials=creds, cache=MemoryCache())
    return service


def extract_from_gsheet():
    service = get_service()

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=BWE_SPREADSHEET_ID,
        valueRenderOption='FORMULA',
        range=BWE_EXTRACT_RANGE
    ).execute()
    values = result.get('values', [])


    if not values:
        print('No data found.')
    else:
        csv_savefile_path = os.path.join(BWE_CSV_SAVE_DIR, BWE_CSV_SAVE_FILENAME)
        print('Saving extracted data to', csv_savefile_path)
        csv_savefile = open(csv_savefile_path, 'w')
        writer = csv.writer(csv_savefile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for row in values:
            # print(row)
            print('Processing row', row)
            writer.writerow(row)
        csv_savefile.close()


if __name__ == '__main__':
    extract_from_gsheet()

