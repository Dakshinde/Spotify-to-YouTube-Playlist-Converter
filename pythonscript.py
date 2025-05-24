import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import time
import os
import config  # Import API keys from config.py

LAST_TRACK_FILE = "last_track.txt"
ADDED_SONGS_FILE = "added_songs.txt"

# 🔹 Authenticate Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=config.SPOTIFY_CLIENT_ID,
    client_secret=config.SPOTIFY_CLIENT_SECRET,
    redirect_uri=config.SPOTIFY_REDIRECT_URI,
    scope="user-library-read"
))

# 🔹 Authenticate YouTube API
def authenticate_youtube():
    flow = InstalledAppFlow.from_client_secrets_file(
        config.GOOGLE_CLIENT_SECRET_FILE,
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"]
    )
    credentials = flow.run_local_server(port=0)
    return build("youtube", "v3", credentials=credentials)

youtube = authenticate_youtube()
print("✅ Spotify & YouTube Authentication Successful!")

# 🔹 Retrieve last added track
def get_last_added_track():
    if os.path.exists(LAST_TRACK_FILE):
        with open(LAST_TRACK_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

# 🔹 Save last added track
def save_last_added_track(track_name):
    with open(LAST_TRACK_FILE, "w", encoding="utf-8") as f:
        f.write(track_name)

# 🔹 Load already added songs
def get_added_songs():
    if os.path.exists(ADDED_SONGS_FILE):
        with open(ADDED_SONGS_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

# 🔹 Save newly added song
def save_added_song(track_name):
    with open(ADDED_SONGS_FILE, "a", encoding="utf-8") as f:
        f.write(track_name + "\n")

# 🔹 Get ALL Spotify Liked Songs (Paginated)
def get_liked_songs():
    songs = []
    results = sp.current_user_saved_tracks(limit=50)

    while results:
        for item in results['items']:
            track = item['track']
            song_name = track['name']
            artist_name = track['artists'][0]['name']
            songs.append(f"{song_name} by {artist_name}")

        results = sp.next(results) if results['next'] else None  # Go to next page
    
    return songs

songs = get_liked_songs()
added_songs = get_added_songs()

# 🔹 Search for a Song on YouTube
def search_youtube_song(song_name):
    try:
        request = youtube.search().list(
            part="snippet",
            q=song_name,
            maxResults=1
        )
        response = request.execute()
        if response["items"]:
            return response["items"][0]["id"]["videoId"], response["items"][0]["snippet"]["title"]
        else:
            print(f"⚠️ No results found for: {song_name}")
            return None, None
    except Exception as e:
        print(f"⚠️ API Error searching for {song_name}: {e}")
        return None, None

# 🔹 Add Video to YouTube Playlist
def add_video_to_playlist(video_id, video_title, playlist_id):
    if video_title.lower() in added_songs:
        print(f"✅ Skipping duplicate: {video_title}")
        return

    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id}
                }
            }
        )
        request.execute()
        print(f"🎵 Added: {video_title} | https://www.youtube.com/watch?v={video_id}")
        save_added_song(video_title.lower())
        time.sleep(2)  # Delay to avoid API quota limits
    except Exception as e:
        print(f"⚠️ Error adding video {video_id}: {e}")

# 🔹 Process Songs & Resume from Last Added Track
playlist_id = "ADD YOUR PLAYLIST ID"
last_track_name = get_last_added_track()
found_last_track = False if last_track_name else True  # If no file, start fresh

for song in songs:
    if not found_last_track:
        if song == last_track_name:
            print("🔄 Resuming from last added track...")
            found_last_track = True  # Now start adding new tracks
        continue  # Skip until we find last added song

    if song in added_songs:
        print(f"⚠️ Skipping already added song: {song}")
        continue
    
    video_id, video_title = search_youtube_song(song)
    if video_id:
        add_video_to_playlist(video_id, video_title, playlist_id)
        save_last_added_track(song)  # Save progress

print("✅ Your Spotify Liked Songs are now on YouTube!")
