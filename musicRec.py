import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.cluster import KMeans
from kneed import KneeLocator
import string
import random
import time
import numpy as np
from flask import Flask, render_template, request

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

app = Flask(__name__)

authLimit = 5000 #limit of requests per day per user
searchLimit = 5 #search API requests to 5 per second per user
otherLimit = 10 #other API requests to 10 per second per user

requestCount = {'search': 0, 'other': 0}
startTime = time.time()


def rateLimiter(limit, requestType):
    global startTime
    currentTime = time.time()

    if currentTime - startTime > 1:
        requestCount['search'] = 0
        requestCount['other'] = 0
        startTime = currentTime
    
    if requestCount[requestType] >= limit:
        sleepTime = 1 - (currentTime-startTime)
        print(f'Rate limit reached for {requestType}. Sleeping for {sleepTime:.2f} seconds')
        time.sleep(sleepTime)
        requestCount['search'] = 0
        requestCount['other'] = 0
        startTime = time.time()
    requestCount[requestType] += 1

#get playlists from user
def getPlaylists():
    playlists = []
    rateLimiter(otherLimit, 'other')
    results = sp.current_user_playlists()
    playlists.extend(results['items'])

    #handle pagination if necessary
    while results['next']:
        rateLimiter(otherLimit, 'other')
        results = sp.next(results)
        playlists.extend(results['items'])

    return playlists

#get tracks from playlist
def getPlaylistTracks(playlistID):
    tracks = []
    rateLimiter(otherLimit, 'other')
    results = sp.playlist_tracks(playlistID)
    tracks.extend(results['items'])

    #handle pagination if necessary
    while results['next']:
        rateLimiter(otherLimit, 'other')
        results = sp.next(results)
        tracks.extend(results['items'])
    
    return tracks


def getAudioFeatures(trackIds, chunkSize = 50):
    features = []
    for i in range(0,len(trackIds), chunkSize):
        chunk = trackIds[i:i+chunkSize]
        rateLimiter(otherLimit, 'other')
        features.extend(sp.audio_features(chunk))
    return features

def getRandomTracks(limit=100):
    #initialize an empty list to store the tracks
    randomTracks = []
    #initialize an empty set to keep track of unique track IDs
    uniqueTrackIDs = set()
    #define a string containing all lowercase letters, uppercase letters, and digits to use to find a random query
    chars = string.ascii_letters + string.digits

    #while loop to get tracks until limit
    while len(randomTracks) < limit:
        query = ''.join(random.choices(chars,k=2))
        rateLimiter(searchLimit, 'search')
        results = sp.search(q=query, type='track',limit=5)
        tracks = results['tracks']['items']

        for track in tracks:
            trackID = track['id']
            if trackID not in uniqueTrackIDs:
                uniqueTrackIDs.add(trackID)
                randomTracks.append(track)
        if len(randomTracks) >= limit:
            break
    
    uniqueTrackIDs = list(uniqueTrackIDs)
    return randomTracks,uniqueTrackIDs

@app.route('/',methods=['GET','POST'])
def index():
    #initialize recommendations
    recommendedTracksArr = []

    #get the playlists
    playlists = getPlaylists()

    #if a number is input into playlistNumber
    if request.method == 'POST':
        playlistNumber = int(request.form['playlistNumber'])-1
        
        if 0 <= playlistNumber < len(playlists):
            selectedPlaylistId = playlists[playlistNumber]['id']
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

        #get random tracks to use to find recommencatin
        randomTracks,uniqueTrackIDs = getRandomTracks(limit=100)
        features2 = getAudioFeatures(uniqueTrackIDs)

        df2 = pd.DataFrame(features2)
        songFeatures2 = df2[['danceability', 'energy', 'key', 'loudness', 'mode', 
                'speechiness', 'acousticness', 'instrumentalness', 'liveness', 
                'valence', 'tempo']]
        
        recommendationPred = bestKmeans.predict(songFeatures2)
        print('recommendation cluster assignments:')
        print(recommendationPred)

        #get user's most common cluster
        userClusterList = bestKmeans.predict(songFeatures)
        userCluster, counts = np.unique(userClusterList, return_counts = True)
        userMainCluster = userCluster[np.argmax(counts)]

        #filter recommendation based on user's cluster
        recommendations = [randomTracks[i] for i in range(len(recommendationPred)) if recommendationPred[i] == userMainCluster]

        #select 5 recommendations
        recommendedTracks = recommendations[:5]
        recommendedTracksArr = [{'name':track['name'], 'artists': [artist['name'] for artist in track['artists']]} for track in recommendedTracks]
        
    return render_template('index.html',playlists=playlists, recommendedTracksArr=recommendedTracksArr)

if __name__ == '__main__':
    app.run(debug=True)


"""def main():
    try:
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

        #get random tracks to use to find recommencatin
        randomTracks,uniqueTrackIDs = getRandomTracks(limit=100)
        features2 = getAudioFeatures(uniqueTrackIDs)

        df2 = pd.DataFrame(features2)
        songFeatures2 = df2[['danceability', 'energy', 'key', 'loudness', 'mode', 
                'speechiness', 'acousticness', 'instrumentalness', 'liveness', 
                'valence', 'tempo']]
        
        recommendationPred = bestKmeans.predict(songFeatures2)
        print('recommendation cluster assignments:')
        print(recommendationPred)

        #get user's most common cluster
        userClusterList = bestKmeans.predict(songFeatures)
        userCluster, counts = np.unique(userClusterList, return_counts = True)
        userMainCluster = userCluster[np.argmax(counts)]

        #filter recommendation based on user's cluster
        recommendations = [randomTracks[i] for i in range(len(recommendationPred)) if recommendationPred[i] == userMainCluster]

        #select 5 recommendations
        recommendedTracks = recommendations[:5]
        print('Recommended Tracks:')
        for track in recommendedTracks:
            artistNames = ', '.join([artist['name'] for artist in track['artists']])
            print(f'{track['name']} by {artistNames}\n' )

    except Exception as e:
        print(f'An error occured: {e}')

if __name__ == '__main__':
    main()"""
