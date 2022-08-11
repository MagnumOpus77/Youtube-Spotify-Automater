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



class LikedVideostoPlaylist:
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
    


    def get_liked_videos(self): 
        """Grab Our Liked Videos & Create A Dictionary Of Important Song Information"""
        
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )
        response = request.execute()

        # collect each video and get important information
        for item in response["items"]:

            try:
                video_title = item["snippet"]["title"]
                youtube_url = "https://www.youtube.com/watch?v={}".format(item["id"])

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

        print(f"{len(self.all_song_info)} out of {len(self.all_song_info)+self.error_vid_count} Youtube Videos have been added to the Spotify Playlist")
        print()
        


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
    print("\t Youtube Liked Songs  ->  New Spotify Playlist")
    print()
    cp = LikedVideostoPlaylist()
    # populate dictionary with our liked songs
    cp.get_liked_videos()
    # create a new playlist
    playlist_id = cp.create_playlist()

    cp.add_songs_to_playlist(playlist_id)