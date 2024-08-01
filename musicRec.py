import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import os

# load .envfile
load_dotenv()

# Access Credentials
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

# Authenticate
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

#get trackID from song title input
def getTrackID(songTitle, artist=None):
    query = f'track:{songTitle}'
    if artist:
        query += f'artist:{artist}'
    results = sp.search(q=query, type='track', limit=1)
    tracks = results['tracks']['items']
    if tracks:
        return tracks[0]['id']
    else:
        print(f'Track not found for {songTitle}')
        return None

def getAudioFeatures(trackIds):
    features = sp.audio_features(trackIds)
    return features


# Prompt user for input
print('insert 5 songs in the form song,artist here separated by semicolon: ')
songInput = input()

# Convert input string to a list of song IDs
songAndArtists = songInput.split(';')

# Remove any leading/trailing whitespace from each song ID
trackIds = []
for songAndArtist in songAndArtists:
    if ',' in songAndArtist:
        sAndA = songAndArtist.split(',')
        songTitle = sAndA[0]
        songTitle = songTitle.strip()
        Artist = sAndA[1]
        Artist = Artist.strip()
    else:
        songTitle = songAndArtist
        Artist = []

    #get audio features
    trackId = getTrackID(songTitle, Artist)
    trackIds.append(trackId)

features = getAudioFeatures(trackIds)
print(features)
