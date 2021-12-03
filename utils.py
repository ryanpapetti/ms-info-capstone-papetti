import json, time, re
from flask import Flask, request, redirect, render_template
import requests
from urllib.parse import quote
import logging, pandas as pd
from scipy.cluster.hierarchy import cut_tree
from sklearn.cluster import KMeans

from scripts import SpotifyUser, Contacter


def gather_cluster_size_from_submission(submission):
    pattern = r'\d+'
    return int(re.findall(pattern, submission)[0])



def prime_user_from_access_token(user_id,accessToken):

    user_contacter = Contacter()
    user_contacter.formAccessHeaderfromToken(accessToken)
    new_user = SpotifyUser(user_id, contacter=user_contacter)
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
        assert algorithm.lower() in ['kmeans', 'agglomerative', 'hierarchical']
        labelled_data = normalized_data.copy()
        if algorithm.lower() == 'kmeans':
            model = KMeans(clusters)
            model.fit(normalized_data)
            cluster_labels = model.labels_
            labelled_data['Label'] = cluster_labels
        elif algorithm.lower() == 'agglomerative':
            linkage_matrix = SpotifyUser.produce_linkage_matrix(normalized_data)
            agglomerative_labels = cut_tree(linkage_matrix,clusters)
            labelled_data['Label'] = agglomerative_labels
        return labelled_data
    except AssertionError:
        raise AssertionError('Algorithm passed is NOT either kmeans or agglomerative')




def prepare_playlists(user,labelled_data):
    return user.generate_uploadable_playlists(labelled_data)

