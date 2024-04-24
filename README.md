# YouTube-Smart-Playlist
A Python script that adds unwatched videos from specified channels to a playlist

## Usage
1. Install Python 3.11 or higher and all of the dependencies in the requirements.txt file.
2. Follow the instructions [on this page](https://developers.google.com/youtube/v3/quickstart/python#step_1_set_up_your_project_and_credentials) to create a YouTube Data API V3 OAuth 2.0 client ID
3. When configuring the Oauth Consent Screen for your application, select the following scopes:
    * https://www.googleapis.com/auth/youtube
    * https://www.googleapis.com/auth/youtube.force-ssl
4. Download the JSON file that contains the credentials and save it in this directory as `client_secrets.json`