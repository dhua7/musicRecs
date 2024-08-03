import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

# load .envfile
load_dotenv()

# Access Credentials
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('REDIRECT_URI')


# Authenticate
sp_oauth = SpotifyOAuth(client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=redirect_uri,
                        scope='playlist-read-private')
sp = spotipy.Spotify(auth_manager=sp_oauth)


#get playlists from user
def getPlaylists():
    playlists = []
    results = sp.current_user_playlists()
    playlists.extend(results['items'])

    #handle pagination if necessary
    while results['next']:
        results = sp.next(results)
        playlists.extend(results['items'])

    return playlists

#get tracks from playlist
def getPlaylistTracks(playlistID):
    tracks = []
    results = sp.playlist_tracks(playlistID)
    tracks.extend(results['items'])

    #handle pagination if necessary
    while results['next']:
        results = sp.next(results)
        tracks.extend(['items'])
    
    return tracks


def getAudioFeatures(trackIds):
    features = sp.audio_features(trackIds)
    return features

def main():
    #retrieve user playlists
    playlists = getPlaylists()

    # Display playlists to the user
    for i, playlist in enumerate(playlists):
        print(f"{i + 1}: {playlist['name']}")

    #prompt user to select a playlist
    playlistIndex = int(input('enter the number of playlists you wnat to view: ')) - 1
    if 0 <= playlistIndex < len(playlists):
        selectedPlaylistId = playlists[playlistIndex]['id']
        tracks = getPlaylistTracks(selectedPlaylistId)
        trackIds = [track['track']['id'] for track in tracks]

        #get audio features for tracks
        features = getAudioFeatures(trackIds)
        print(features)

    else:
        print('Invalid playlist number')

if __name__ == '__main__':
    main()
