"""
Shows basic usage of the Drive v3 API.

Creates a Drive v3 API service and prints the names and ids of the last 10 files
the user has access to.
"""
from __future__ import print_function
from apiclient.discovery import build, MediaFileUpload
from httplib2 import Http
from oauth2client import file, client, tools

# Setup the Drive v3 API
SCOPES = 'https://www.googleapis.com/auth/drive'
store = file.Storage('credentials.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('drive', 'v3', http=creds.authorize(Http()))

import sys, os
if len(sys.argv) == 0:
    sys.exit(0)
if sys.argv[1] == "upload":
    # Call the Drive v3 API
    fullpath = sys.argv[2]
    remotepath = sys.argv[3]
    parent = sys.argv[4]
    file_metadata = {"name": remotepath, "parents": [parent]}
    media = MediaFileUpload(fullpath, mimetype="application/pgp-encrypted")
    f = service.files().create(body = file_metadata, media_body = media, fields = "id").execute()
    print("Uploaded " + str(f.get("id")))
else:
    # create folder
    parent = sys.argv[2]
    child = sys.argv[3]
    file_metadata = {"name": child, "mimeType": "application/vnd.google-apps.folder"}
    print(service.files().create(body = file_metadata, fields="id").execute().get("id"))
