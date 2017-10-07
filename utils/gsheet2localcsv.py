from __future__ import print_function
import csv
import httplib2
import os


from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'credentials/client_secret.json'
APPLICATION_NAME = 'Download Google Sheet Data using API call'


# EXTRACT SETTINGS
BWE_SPREADSHEET_ID = '1oGmEK7cGqMefFRE4brTsoyI9KoKydIM8E54kcNIiVds'
BWE_SHEET_NAME = 'OVERALL DATABASE'
BWE_RANDE = 'A8:G378'
BWE_EXTRACT_RANGE = BWE_SHEET_NAME + '!' + BWE_RANDE
BWE_CSV_SAVE_DIR = os.path.join(os.path.dirname(__file__), os.path.pardir)  # project root dir is .. from utils/
BWE_CSV_SAVE_FILENAME = 'bwe_overall_database.csv'




def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-download-google-sheet-data.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
    """Downloads
    Shows basic usage of the Sheets API.

    Creates a Sheets API service object and prints the names and majors of
    students in a sample spreadsheet:
    https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    # EXTRACT DATA USING API CALL
    result = service.spreadsheets().values().get(
        spreadsheetId=BWE_SPREADSHEET_ID,
        range=BWE_EXTRACT_RANGE,
        valueRenderOption='FORMULA',
    ).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        print('Saving data to file ' + BWE_CSV_SAVE_FILENAME + ' in dir ' + os.path.abspath(BWE_CSV_SAVE_DIR) )

        csv_savefile_path = os.path.join(BWE_CSV_SAVE_DIR,BWE_CSV_SAVE_FILENAME)
        print(csv_savefile_path)
        csv_savefile = open(csv_savefile_path, 'w')
        writer = csv.writer(csv_savefile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for row in values:
            # print(row)
            print('Processing row', row[3])
            writer.writerow(row)

        csv_savefile.close()

if __name__ == '__main__':
    main()

