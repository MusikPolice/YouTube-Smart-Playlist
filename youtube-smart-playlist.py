import argparse
from dataclasses import dataclass
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors


def get_authenticated_service(client_secrets_file):
    # disable OAuthlib's HTTPS verification when running locally
    # TODO: this seems stupid. probably don't do this
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # do the oauth dance and return an authenticated api client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, 
        ["https://www.googleapis.com/auth/youtube.readonly"]   # TODO: probably need write permissions to manage playlists
    )
    credentials = flow.run_local_server()
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)


# gets all of the authenticated user's playlists
# the return type is a dictionary with key playlist name and value playlist id
# TODO: this should return a list of dataclass just like other methods
def get_playlists(youtube):
    results = {}
    paginationToken = None
    while True:
        # fetch a page
        response = youtube.playlists().list(
            part="snippet,contentDetails",
            mine=True,
            maxResults=50,
            pageToken=paginationToken
        ).execute()

        # extract the results
        for item in response["items"]:
            results[item["snippet"]["title"]] = item["id"]
        
        # handle pagination if necessary
        if 'nextPageToken' in response:
            paginationToken = response['nextPageToken']
        else:
            break
    
    return results


# creates a playlist with the specified name and description
# returns the unique id of the newly created playlist
# TODO: googleapiclient.errors.HttpError: <HttpError 403 when requesting https://youtube.googleapis.com/youtube/v3/playlists?part=snippet%2Cstatus&alt=json returned "Request had insufficient authentication scopes.". Details: "[{'message': 'Insufficient Permission', 'domain': 'global', 'reason': 'insufficientPermissions'}]">
# need to list the required scopes in the README.md
def create_private_playlist(name, description, youtube):
    response = youtube.playlists().insert(
        part="snippet,status",
        body=dict(
            snippet=dict(
                title=name,
                description=description
            ),
            status=dict(
                privacyStatus="private"
            )
        )
    ).execute()
    return response["id"]


@dataclass
class PlaylistVideo:
    video_id: str
    video_title: str
    channel: str
    channel_id: str

# gets all of the videos in the playlist with the specified id
# the return type is a list of PlaylistVideo objects
def get_videos_in_playlist(playlist_id, youtube):
    results = []
    paginationToken = None
    while True:
        # fetch a page
        response = youtube.playlistItems().list(
            part="snippet",
            maxResults=50,
            playlistId=playlist_id
        ).execute()

        # extract the results
        for item in response["items"]:
            results.append(
                PlaylistVideo(
                    item["snippet"]["resourceId"]["videoId"],
                    item["snippet"]["title"],
                    item["snippet"]["videoOwnerChannelTitle"],
                    item["snippet"]["videoOwnerChannelId"]
                )
            )

        # handle pagination if necessary
        if 'nextPageToken' in response:
            paginationToken = response['nextPageToken']
        else:
            break

    return results


def main(args):
    # get a youtube api client
    youtube = get_authenticated_service('client_secrets.json')

    # testing: print out all the methods available on the client
    # print([method for method in dir(youtube) if callable(getattr(youtube, method)) and not method.startswith('__')])

    # if the managed playlist doesn't exist in the authenticated account, create it
    playlists = get_playlists(youtube)
    if not args.playlist_name in playlists.keys():
        playlist_id = create_private_playlist(args.playlist_name, "Managed by YouTube-Smart-Playlist", youtube)
        playlists[args.playlist_name] = playlist_id

    print(get_videos_in_playlist(playlists[args.playlist_name], youtube))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--playlist_name', type=str, help='The name of the managed playlist. This playlist will be created if it does not already exist.')
    args = parser.parse_args()
    main(args)