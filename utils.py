import json, time, re, logging, random
from flask import current_app, jsonify
import requests
from urllib.parse import quote
import logging, pandas as pd
from scipy.cluster.hierarchy import cut_tree
from sklearn import cluster
from sklearn.cluster import KMeans

from scripts import SpotifyUser, Contacter

random.seed(420)

# logging.formatter
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def gather_cluster_size_from_submission(submission):
    pattern = r'\d+'
    return int(re.findall(pattern, submission)[0])



def prime_user_from_access_token(user_id,accessToken):

    user_contacter = Contacter()
    user_contacter.formAccessHeaderfromToken(accessToken)
    new_user = SpotifyUser(user_id, contacter=user_contacter)
    logging.info('user has been primed from access token')
    return new_user


def prepare_data(user):
    logging.info('Timing how long data collection and storing takes')
    start_time = time.time()
    aggregated_audio_features = user.collect_data()
    logging.info(f'The elapsed time is {time.time() - start_time} seconds')
    user_prepped_data = user.prepare_data_for_clustering(aggregated_audio_features)

    normalized_data = SpotifyUser.normalize_prepped_data(user_prepped_data)
    return normalized_data



def execute_clustering(algorithm, clusters, normalized_data):
    try:
        assert algorithm.lower() in ['kmeans', 'agglomerative hierarchical']
        labelled_data = normalized_data.copy()
        if algorithm.lower() == 'kmeans':
            model = KMeans(clusters)
            model.fit(normalized_data)
            cluster_labels = model.labels_
            labelled_data['Label'] = cluster_labels
        elif algorithm.lower() == 'agglomerative hierarchical':
            logging.info('Working with agglomerative hierarchical')
            linkage_matrix = SpotifyUser.produce_linkage_matrix(normalized_data)
            agglomerative_labels = cut_tree(linkage_matrix,clusters)
            labelled_data['Label'] = agglomerative_labels
        return labelled_data
    except AssertionError:
        raise AssertionError('Algorithm passed is NOT either kmeans or agglomerative hierarchical')




def prepare_playlists(user,labelled_data):
    return user.generate_uploadable_playlists(labelled_data)


def get_cluster_playlist_metadata(clustered_tracks):
    total_tracks = sum([len(tracks) for tracks in clustered_tracks.values()])
    total_organized_playlist_data = {}
    for playlist, tracks in clustered_tracks.items():
        logging.info(f'working with clustered playlist {playlist}')
        tracks_to_be_displayed = tracks[:5]
        centroid_track = tracks_to_be_displayed[0]
        playlist_size = len(tracks)
        playlist_proportion = round(100 * round(playlist_size/total_tracks, 3), 3)
        organized_playlist_data = {'centroid_track':centroid_track, 'displayable_tracks':tracks_to_be_displayed, 'size': format(playlist_size, ","), 'proportional_size': playlist_proportion}
        total_organized_playlist_data[playlist] = organized_playlist_data
    return total_organized_playlist_data


def get_displayable_tracks_metadata(authorization_header,track_ids):
    track_ids_string = ','.join(track_ids)
    query_params = f'?ids={track_ids_string}'
    retrieved_metadata = requests.get(f'https://api.spotify.com/v1/tracks{query_params}', headers=authorization_header).json()

    total_track_metadata = []

    for track_data in retrieved_metadata['tracks']:
        # i just need the name and the album cover and url to play
        track_name = track_data['name']
        artists = ' / '.join([artist['name'] for artist in track_data['artists']])
        playable_url = track_data['external_urls']['spotify']
        album_cover_url = track_data['album']['images'][0]['url']
        track_metadata = {'name': track_name, 'playable_url':playable_url, 'album_cover_url':album_cover_url, 'artists':artists}
        total_track_metadata.append(track_metadata)
    
    return dict(zip(track_ids,total_track_metadata))


def organize_cluster_data_for_display(authorization_header,clustered_tracks):
    total_organized_playlist_data = get_cluster_playlist_metadata(clustered_tracks)

    displayable_data = {}

    for playlist_id, data in total_organized_playlist_data.items():
        tracks_metadata = get_displayable_tracks_metadata(authorization_header, data['displayable_tracks'])
        displayable_data[playlist_id] = tracks_metadata
    
    return displayable_data, total_organized_playlist_data



def get_deployed_cluster_obj(deployed_cluster_objs, cluster_id):
    cluster_id = int(cluster_id) if type(cluster_id) == str else cluster_id

    return deployed_cluster_objs[cluster_id]

def load_proper_cluster_button(session,cluster_id):
    logging.info(f'Passed cluster_id {cluster_id} ({type(cluster_id)})')
    if 'DEPLOYED_CLUSTERS_OBJS' in session:
        logging.info(f"DEPLOYED CLUSTERS ARE: {session['DEPLOYED_CLUSTERS_OBJS']} ")
        logging.info(f"Cluster ID ({cluster_id}) and set of keys of objects ({set(session['DEPLOYED_CLUSTERS_OBJS'].keys())})")
        if cluster_id in session['DEPLOYED_CLUSTERS_OBJS']:
            return 'listen'
    return 'deploy'