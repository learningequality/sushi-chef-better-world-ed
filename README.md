# Better World Ed Chef

Sushi chef for `Better World Ed` - Import content from `Better World Ed` into `Kolibri Studio`


## Installation

* Install [Python 3](https://www.python.org/downloads/) if you don't have it already.

* Install [pip](https://pypi.python.org/pypi/pip) if you don't have it already.

* Create a Python virtual environment for this project (optional, but recommended):
   * Install the virtualenv package: `pip install virtualenv`
   * The next steps depends if you're using UNIX (Mac/Linux) or Windows:
      * For UNIX systems:
         * Create a virtual env called `venv` in the current directory using the
           following command: `virtualenv -p python3  venv`
         * Activate the virtualenv called `venv` by running: `source venv/bin/activate`.
           Your command prompt will change to indicate you're working inside `venv`.
      * For Windows systems:
         * Create a virtual env called `venv` in the current directory using the
           following command: `virtualenv -p C:/Python36/python.exe venv`.
           You may need to adjust the `-p` argument depending on where your version
           of Python is located.
         * Activate the virtualenv called `venv` by running: `.\venv\Scripts\activate`

* Run `pip install -r requirements.txt` to install the required python libraries.


## Usage
##### Get an Authorization Token
In order to run the script, you need an authorization token. To get one,
  1. Create an account on [Kolibri Studio](https://contentworkshop.learningequality.org/)
  2. Navigate to the Tokens tab under your Settings page
  3. Copy the given authorization token (you will need this for later).


## Requirements
This sushi chef requires following components:
  - `credentials/client_secret.json`: Google API client information for OAuth
  - `credentials/vimeo_api_client.json`: Vimeo API client info

These files must be obtained separately from the git repo. Ask in the #suchi-chefs channel on slack.



## Running

### Step 1: extract data

First run the extract script
```bash
./extract.py
```

This will produce the CSV file `chefdata/Better_World_Ed_Content_shared_for_Kolibri.csv`




## Step 2: Running the Chef

In `sushi-chef-better-world-ed` directory, run the following command to run the script with token from previous step:
```bash
./sushichef.py  -v --reset --thumbnails  --token=STUDIOTOKENGOESHERE --stage
```





## Special install instructions

If you get the error `ImportError: pycurl: libcurl link-time ssl backend (openssl) is different from compile-time ssl backend (none/other)`
when running on Mac, you can workaround using


```bash
brew install curl-openssl
set -x PYCURL_CURL_CONFIG "/usr/local/opt/curl-openssl/bin/curl-config"
set -x LDFLAGS '-L/usr/local/opt/openssl/lib -L/usr/local/opt/c-ares/lib -L/usr/local/opt/nghttp2/lib -L/usr/local/opt/libmetalink/lib -L/usr/local/opt/rtmpdump/lib -L/usr/local/opt/libssh2/lib -L/usr/local/opt/openldap/lib -L/usr/local/opt/brotli/lib'
set -x CPPFLAGS "-I/usr/local/opt/openssl/include"
pip install pycurl --compile --no-cache-dir
```
