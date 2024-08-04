import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.cluster import KMeans
from kneed import KneeLocator

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
    playlistIndex = int(input('enter the number of the playlist you wnat to view: ')) - 1
    if 0 <= playlistIndex < len(playlists):
        selectedPlaylistId = playlists[playlistIndex]['id']
        tracks = getPlaylistTracks(selectedPlaylistId)
        trackIds = [track['track']['id'] for track in tracks]

        #get audio features for tracks
        features = getAudioFeatures(trackIds)
        print(features)

    else:
        print('Invalid playlist number')
    
    #convert features to dataframe
    df = pd.DataFrame(features)

    # Select relevant features for clustering
    songFeatures = df[['danceability', 'energy', 'key', 'loudness', 'mode', 
               'speechiness', 'acousticness', 'instrumentalness', 'liveness', 
               'valence', 'tempo']]
    
    #split data into training, validation, and test set
    trainData, tempData = train_test_split(songFeatures, test_size = 0.3, random_state=42)
    validationData,testData = train_test_split(tempData, test_size=0.5, random_state=42)

    #train the model
    #create arr of values for diff numbers of clusters we want to try
    numClusters = range(2,11)

    kMeansArr = []
    inertia = []
    #inertia is sum of squared distance between each data point and centroid of cluster to which it belonds
    #lower inertia generally implies tighter clusters

    for k in numClusters:
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(trainData)
        inertia.append(kmeans.inertia_)
        kMeansArr.append(kmeans)

    #find the elbow point using KneeLocator
    elbowPointFind = KneeLocator(range(2,11), inertia, curve='convex', direction='decreasing')
    bestNumClusters = elbowPointFind.elbow
    bestKmeans = kMeansArr[bestNumClusters-1]    

    print(f'Best number of clusters: {bestNumClusters}')
    
    #evaluate the best model on the validation set
    validationPred = bestKmeans.predict(validationData)

    #evaluate best model on test set
    testPred = bestKmeans.predict(testData)

   # print test set cluster assignments
    print('Test set cluster assignments:')
    print(testPred)

if __name__ == '__main__':
    main()
