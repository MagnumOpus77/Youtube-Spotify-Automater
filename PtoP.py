import json
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import requests
import youtube_dl

from secrets import spotify_token, spotify_user_id

class ExpiredKeyError(Exception):
    pass


class Playlist:
    def __init__(self, id, title):
        self.id = id
        self.title = title


class PlaylisttoPlaylist:
    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}
        self.error_vid_count = 0
    

    def get_youtube_client(self):
        """ Log Into Youtube, Copied from Youtube Data API """

        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        try:
            # Get credentials and create an API client
            scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes)
            credentials = flow.run_console()

            # from the Youtube DATA API
            youtube_client = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
            return youtube_client
        except Exception:
            print("   Invalid Authorization Code")
            quit()
    
    

    def get_playlists(self):
        request = self.youtube_client.playlists().list(
            #part="snippet,contentDetails",
            #channelId = "UC_x5XG1OV2P6uZZ5FSM9Ttw",
            #channel_Id="RuuXzTIr0OoDqI4S0RU6n4FqKEM",
            part="id, snippet",
            maxResults=25,
            mine=True
        )
 
        response = request.execute()
        #playlists = [playlist["id"] for playlist in response["items"]]
        playlists = [Playlist(item["id"], item["snippet"]["title"]) for item in response["items"]]

        # list of playlist id's
        return playlists



    def get_vids_from_playlist(self, yt_playlist_id):
        songs = []
        print(yt_playlist_id)
        request = self.youtube_client.playlistItems().list(
            playlistId=yt_playlist_id,
            #part="id, snippet"
            part = "id, snippet,contentDetails"
        )
        print('hi')
        response = request.execute()
        print('hii')

        # list (multiple video IDs)

        for item in response['items']:
            try:
                video_title = item["snippet"]["title"]
                video_id = item["snippet"]["resourceId"]["videoId"]
                youtube_url = f"https://www.youtube.com/watch?v={video_id}"

                # use youtube_dl to collect the song name & artist name
                print("[Extracting Video...]", end="  ")
                video = youtube_dl.YoutubeDL({"quiet": True}).extract_info(youtube_url, download=False)
                artist = video["artist"]
                song_name = video["track"]
                print(f"{song_name} - {artist}")

                if song_name is not None and artist is not None:
                    # save all important info and skip any missing song and artist
                    self.all_song_info[video_title] = {
                        "youtube_url": youtube_url,
                        "song_name": song_name,
                        "artist": artist,
                        
                        # add the uri, easy to get song to put into playlist
                        "spotify_uri": self.spotify_search_song(artist, song_name)
                    }

            except ExpiredKeyError:
                quit()
            except KeyError:
                self.error_vid_count += 1
                print(f"\n   This video didn't get extracted. ({self.error_vid_count})")



    def create_playlist(self):
        """Create A New Playlist"""
        playlist_name = ""
        while playlist_name == "":
            playlist_name = input("Name your playlist: ")
        playlist_description = input("Enter a description for your playlist: ")
        playlist_public = False
        if input("Type 'public' to make your playlist public: ").strip() == "public":
            playlist_public = True


        request_body = json.dumps({
            "name": playlist_name,
            "description": playlist_description,
            "public": playlist_public
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_user_id)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {spotify_token}"
            }
        )
        response_json = response.json()

        # playlist id
        return response_json["id"]



    def spotify_search_song(self, artist, song_name):
        """Search For the Song"""
        #query = f"https://api.spotify.com/v1/search?q={q}&type=track"
        query = f"https://api.spotify.com/v1/search?query=track%3A{song_name}+artist%3A{artist}&type=track&offset=0&limit=20"
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {spotify_token}"
            }
        )

        try:
            response_json = response.json()
            song_results = response_json["tracks"]["items"] # should this be in the else? bc it doesn't raise error
        except:
            print("KeyError... spotify token is expired")
            print("Go here to reset: https://developer.spotify.com/console/post-playlists/\n")
            raise ExpiredKeyError
        else:
            if song_results:
                # only use the first song
                uri = song_results[0]["uri"]
                return uri
            else:
                raise Exception(f"No song found for {artist} = {song_name}")



    def add_songs_to_playlist(self, playlist_id):
        """Add all liked songs into a new Spotify playlist"""

        # collect all of uri
        uris = [info["spotify_uri"] for song, info in self.all_song_info.items()]

        # add all songs into new playlist
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {spotify_token}"
            }
        )

        # check for valid response status
        if response.status_code not in (200,201):
            print("- ERROR -")
            print("response code:", response.status_code)
            quit()

        # partial success? if error_vid_count is greater than 0?
        print(f"\nDone! {len(self.all_song_info)} liked Youtube Videos were added to your playlist")
        response_json = response.json()

        



def run():
    print("\t Youtube Playlist  ->  New Spotify Playlist")
    print()
    cp = PlaylisttoPlaylist()
    
    
    # Get list of Youtube Playlists
    playlists = cp.get_playlists()
    
    
    # Ask which playlist we want to automate
    for i, playlist in enumerate(playlists):
        print(f"[{i+1}] {playlist.title}")
    
    while True:
        try:
            playlist_num = int(input("Enter the playlist number you wish to add to Spotify Liked Songs: "))
            if playlist_num > len(playlists):
                print("Index out of range")
            else:
                break
        except ValueError:
            print("Enter integer value")
    
    
    # for each video in plalist, get song info from Youtube
    songs = cp.get_vids_from_playlist(playlists[playlist_num-1].id)


    # create a new playlist
    playlist_id = cp.create_playlist()

    cp.add_songs_to_playlist(playlist_id)


    # ok so the problem is...

        # the Youtube Video has to be the song name ONLY
        # the uploader is the artist

        # otherwise... it doesn't extract