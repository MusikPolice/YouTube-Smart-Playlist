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
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file (
        client_secrets_file, 
        [
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ]
    )
    credentials = flow.run_local_server()   # TODO: cache this credentials object to avoid having to redo the oauth flow every time
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)


@dataclass
class Playlist:
    playlist_id: str
    playlist_name: str


# gets all of the authenticated user's playlists
# the return type is a list of Playlist objects
def get_playlists(youtube):
    results = []
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
            results.append(
                Playlist(item["id"], item["snippet"]["title"])
            )
        
        # handle pagination if necessary
        if 'nextPageToken' in response:
            paginationToken = response['nextPageToken']
        else:
            break
    
    return results


# creates a playlist with the specified name and description
# returns the unique id of the newly created playlist
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
class Video:
    video_id: str
    video_title: str
    channel: str
    channel_id: str


# gets all of the videos in the playlist with the specified id
# the return type is a list of Video objects
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
                Video(
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


# returns the unique channel id for the specified channel handle, or None if the specified handle does not exist
def get_channel_id(channel_handle, youtube):
    response = youtube.channels().list(
        part="id",
        forHandle=channel_handle
    ).execute()

    if 'items' in response:
        return response['items'][0]['id']
    else:
        return None


# gets the most recent 10 videos from the specified channel that match the specified query string
# the return type is a list of Video objects, and results are ordered by publish date descending
# this method does not handle pagination - only the first page of results will be returned
def get_videos_from_channel(query, channel_id, youtube):
    response = youtube.search().list(
        q=query,
        part="id,snippet",
        channelId=channel_id,
        maxResults=10,
        order="date",
        type="video",
    ).execute()

    return [
        Video (
            result["id"]["videoId"], 
            result["snippet"]["title"], 
            result["snippet"]["channelTitle"], 
            result["snippet"]["channelId"]
        ) for result in response["items"]
    ]


def main(args):
    # get a youtube api client
    youtube = get_authenticated_service('client_secrets.json')

    # if the managed playlist doesn't exist in the authenticated account, create it
    playlists = get_playlists(youtube)
    if not any(playlist.playlist_name.lower() == args.managed_playlist_name.lower() for playlist in playlists):
        managed_playlist_id = create_private_playlist(args.managed_playlist_name, "Managed by YouTube-Smart-Playlist", youtube)
        playlists.append(Playlist(managed_playlist_id, args.managed_playlist_name))
        print(f"Created managed playlist {args.managed_playlist_name} with id {managed_playlist_id}")

    # the list of video ids that already exist in the managed playlist
    managed_playlist_id = next((pl.playlist_id for pl in playlists if pl.playlist_name == args.managed_playlist_name), None)
    print(f"Fetching existing videos in the {args.managed_playlist_name} playlist with id {managed_playlist_id}")
    managed_video_ids = [video.video_id for video in get_videos_in_playlist(managed_playlist_id, youtube)]

    # the list of videos that match the query in the target channel
    print(f"Fetching videos that match the query string {args.query} from channel with handle {args.channel_handle}")
    channel_id = get_channel_id(args.channel_handle, youtube)
    print(f"The channel id for {args.channel_handle} is {channel_id}")
    matching_video_ids = [video.video_id for video in get_videos_from_channel(args.query, channel_id, youtube)]

    # TODO: there is no way to check watch status of any video :/

    video_ids_to_add_to_managed_playlist = [video_id for video_id in matching_video_ids if video_id not in managed_video_ids]
    print(video_ids_to_add_to_managed_playlist)
    # TODO: add the videos to the managed playlist


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--managed_playlist_name', type=str, required=True, help='The name of the managed playlist. This playlist will be created if it does not already exist.')
    parser.add_argument('--channel_handle', type=str, required=True, help='The handle of the channel to pull unwatched videos from')    # TODO: support multiple channels
    parser.add_argument('--query', type=str, help='An optional query string that video title/description text has to match in order to be added to the managed playlist.')
    args = parser.parse_args()
    main(args)