
import logging, pandas as pd
from scipy.cluster.hierarchy import cut_tree
from sklearn.cluster import KMeans

from new_user import SpotifyUser
from api_contacter import Contacter 

import json

def prime_general_user():
    desired_user_contacter = Contacter()
    desired_user_contacter.gather_auth_hash('../credentials/auth_hash.txt')
    desired_user_contacter.prime_auth_header()
    desired_user_contacter.refreshTheToken('AQAEriHyJqE4DiIyrMiTi8OiYgVZNwbAo1eA5ye8f9ulaQZlJudmk2FVwdfSHcGZQbUXLTcH920YQlK4uWWOMJNOQ2sB0cgOW6Gc-WMUv4p87AZ8mIBm47JbLkBHuGhkthU')
    desired_user = SpotifyUser('1232063482', contacter=desired_user_contacter, optional_display_id = 'Michelle Tracks') #my id stays to add to playlists
    return desired_user


def explore_clusterings(user,normalized_data):
    
    if isinstance(normalized_data,pd.DataFrame):
        normalized_data = normalized_data.values
    
    kmeans_data = SpotifyUser.evaluate_kmeans_clusterings(normalized_data)

    user.plot_inertias_db_scores(*kmeans_data)

    linkage_matrix = SpotifyUser.produce_linkage_matrix(normalized_data)

    user.plot_dendrogram(linkage_matrix)



def execute_clusterings(kmeans_number, agglomerative_number, normalized_data):
    kmeans_model = KMeans(kmeans_number)
    kmeans_model.fit(normalized_data)
    kmeans_labels = kmeans_model.labels_

    linkage_matrix = SpotifyUser.produce_linkage_matrix(normalized_data) 
    agglomerative_labels = cut_tree(linkage_matrix,agglomerative_number)

    return kmeans_labels, agglomerative_labels



def main():
    logging.basicConfig(filename='../logs/michelle_tracks_upload.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')
    og_audio_features = json.load(open('../data/Michelle Pop and Rock Hits Oct 27 2021_tracks.json'))

    top_tracks_user = prime_general_user()

    logging.info('Beginning clustering')

    top_tracks_prepped_data = top_tracks_user.prepare_data_for_clustering(og_audio_features)

    normalized_data = SpotifyUser.normalize_prepped_data(top_tracks_prepped_data)

    explore_clusterings(top_tracks_user,normalized_data) #found kmeans to be 6 and agglomerative to be 9

    kmeans_labelled_data = top_tracks_prepped_data.copy()
    agglomerative_labelled_data = top_tracks_prepped_data.copy()

    kmeans_labels, agglomerative_labels = execute_clusterings(kmeans_number=5, agglomerative_number= 9, normalized_data = normalized_data)

    kmeans_labelled_data['Label'] = kmeans_labels
    agglomerative_labelled_data['Label'] = agglomerative_labels

    kmeans_uploadable_playlists = top_tracks_user.generate_uploadable_playlists(kmeans_labelled_data)
    agglomerative_uploadable_playlists = top_tracks_user.generate_uploadable_playlists(agglomerative_labelled_data)

    top_tracks_user.add_cluster_playlists(kmeans_uploadable_playlists)
    top_tracks_user.add_cluster_playlists(agglomerative_uploadable_playlists, cluster_algo='Agglomerative')










if __name__ == '__main__':
    main()


