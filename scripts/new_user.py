'''
Ryan Papetti

Spotify User

This script hopefully aims to control the User class that can hold playlists, etc.

'''
import json, logging, pandas as pd, numpy as np
from sklearn import preprocessing, metrics
from sklearn.cluster import KMeans
from playlist import Playlist
from track import Track


class SpotifyUser:
    def __init__(self, spotify_id, playlists = {}, contacter = None):
        '''
        The SpotifyUser instance represents a particular Spotify user denoted by a Spotify_id and allows for API communication, storage of playlists, and clustering of tracks.

        __init__(self, name, spotify_id, playlists = {}, contacter = None)

        name - a str representing the name of the user. Note it does not have to match the actual display name of the user.

        spotify_id - a str of the desired user's Spotify ID. It can be obtained from the Spotfiy account or by sharing a user and taking the last part of the URI

        playlists = {} - a dictionary of playlist ids to Playlist instances

        contacter = None - a Contacter if desired. A contacter is used to make API queries and is necessary to do so. However, all database information can be made without a contacter
        '''
        self.name = None
        self.user_id = spotify_id
        self.playlists = playlists
        self.contacter = contacter
 
    

    def get_all_playlist_ids(self):
        '''
        get_all_playlist_ids(self)

        This function calls https://api.spotify.com/v1/users/{self.user_id}/playlists to retrieve the playlist_id of every user playlist. I believe this only includes public playlists. If the user has over 1500 playlists, a Permission error is raised (to avoid drastic amounts of queries, but likely needs to be changed). If there is no contacter, a ValueError is raised. If over 30 queries were made. but fewer were expected, a ValueError is raised.

        This returns a set of tuples, where each tuple is of the form (playlist id, platlist name)
        '''
        if self.contacter is None:
            raise ValueError('Add a contacter!')
        logging.info('Working on hitting the users playlists endpoint')
        link = f'https://api.spotify.com/v1/users/{self.user_id}/playlists'
        api_response = self.contacter.contact_api(link).json()
        final_ids = []
        playlists = api_response['items']
        playlists_to_extend = []
        for playlist in playlists:                
            playlist_name = playlist['name']
            
            logging.info(f'Working with {playlist_name}')

            if playlist['owner']['id'] == self.user_id:
                logging.info(playlist['owner'])
                playlists_to_extend.append((playlist['id'],playlist['name']))
            final_ids.extend(playlists_to_extend)
        total_queries_made = 1
        while api_response['next']: #call the api until you collect all playlists
            new_link = api_response['next']
            api_response = self.contacter.contact_api(new_link).json()
            playlists = api_response['items']
            playlists_to_extend = []
            for playlist in playlists:                
                if playlist['owner']['id'] == self.user_id:
                    playlists_to_extend.append((playlist['id'],playlist['name']))
                final_ids.extend(playlists_to_extend)
            total_queries_made +=1
        
        logging.info(f'Collected all data in {total_queries_made} queries')
        
        return set(final_ids)





    
    def get_all_playlist_information(self):
        '''
        get_all_playlist_information(self)

        Calls self.get_all_playlist_ids() and fills out self.playlists with the Playlist() instances

        Raises an error is self.contacter is None.

        This returns None but updates self.playlists in place

        '''

        if self.contacter is None:
            raise ValueError('Add a contacter')
        playlist_ids = self.get_all_playlist_ids()

        for playlist_info in playlist_ids:
            #make a playlist instance and add it to the user's playlist dict
            playlist_id,playlist_name = playlist_info
            self.playlists[playlist_id] = Playlist(playlist_id,playlist_name)
            self.playlists[playlist_id].retrieve_playlist_data(self.contacter, save_file = True)





    def aggregate_track_ids_across_playlists(self):
        assert self.playlists != {}
        track_set = set()
        for playlist_id, playlist in self.playlists.items():
            logging.info(f'WORKING WITH {playlist_id}')
            relevant_track_ids = {track.id for track in playlist.tracks}
            track_set = (track_set | relevant_track_ids)
        
        if None in track_set:
            track_set.remove(None)

        return track_set

    


    def gather_audio_features_data_from_specified_tracks(self,track_ids):
        assert len(track_ids) > 0

        final_audio_features_data = {}

        track_ids = tuple(track_ids)


        #now determine the number of bins
        bin_num = len(track_ids) // 100 + bool(len(track_ids) % 100)
        custom_bins = [i * 100 for i in range(bin_num)]
        custom_bins.append(len(track_ids))

        for ind in range(len(custom_bins) - 1):
            #download i - i+1
            logging.info(f'On bin {ind + 1} out of {len(custom_bins)-1}')
            relevant_track_ids = track_ids[custom_bins[ind]: custom_bins[ind+1]]
            track_ids_to_download = ','.join(relevant_track_ids)
            additional_q_params = {'ids': track_ids_to_download} 
            endpoint = 'https://api.spotify.com/v1/audio-features'
            response_obj = self.contacter.contact_api(endpoint, additional_request_parameters=additional_q_params)
            logging.info('Retrieved data')
            features = response_obj.json()['audio_features']
            sub_feature_dict = dict(zip(relevant_track_ids,features))
            final_audio_features_data.update(sub_feature_dict)
        return final_audio_features_data
        


    def save_audio_features_data(self,audio_features_data, filepath):
        logging.info(f'Dumping audio features data to {filepath}')
        with open(filepath,'w') as writer:
            json.dump(audio_features_data,writer)
    


    def load_audio_features_data(self, filepath):
        logging.info(f'Loading audio features data from {filepath}')
        with open(filepath) as reader:
            return json.load(reader)

   

    def collect_and_store_data(self, final_storage_path): #THIS MAY BE EXPANDED UPON SIGNIFICANTLY
        '''
        collect_and_store_data(self)

        This function collects all data for the user in the following sense:

        - creates user database
        - retrieves all playlist ids
        - populates the user's playlist info

        - retrieves all audio features for all tracks
        '''
        logging.info('Gathering all playlist info')
        self.get_all_playlist_information()
        for playlist in self.playlists.values():
            playlist.convert_raw_track_items()
        logging.info('Converted all raw track items')
        specified_tracks = self.aggregate_track_ids_across_playlists()
        aggregated_audio_features_data = self.gather_audio_features_data_from_specified_tracks(specified_tracks)

        self.save_audio_features_data(aggregated_audio_features_data,final_storage_path)


    

    def prepare_data_for_clustering(self,aggregated_audio_features_data, alternative_features=None):
        aggregated_audio_features_data_copy = aggregated_audio_features_data.copy()
        
        if alternative_features is not None:
            features = [
            "danceability",
            "energy",
            "loudness",
            "speechiness",
            "acousticness",
            "instrumentalness",
            "liveness",
            "valence",
            "tempo",
            "duration_ms"]
        else:
            features = alternative_features
        
        prepped_features = {}

        for track_id, track_features in aggregated_audio_features_data_copy.items():


            prepped_features[track_id] = {key:val for key,val in track_features.items() if key in features}
        
        return pd.DataFrame(prepped_features).T

    @staticmethod
    def normalize_prepped_data(prepped_data):
        scaler = preprocessing.MinMaxScaler()
        normalized_data = scaler.fit_transform(prepped_data)
        normalized_data_df = pd.DataFrame(normalized_data, columns=prepped_data.columns, index=prepped_data.index)
        return normalized_data_df


    @staticmethod
    def cluster_data(normalized_data, initialized_model):
        return initialized_model.fit_transform(normalized_data)


    
    def evaluate_kmeans_clusterings(self,normalized_data):
        inertias = []
        davies_bouldin_scores = []

        for k in range(1, 51):
            model = KMeans(n_clusters=k, random_state=0)
            model.fit(normalized_data) #fit/train the model
            labels = model.labels_
            davies_bouldin_scores.append(metrics.davies_bouldin_score(normalized_data, labels))
            inertias.append(model.inertia_)
    
        return inertias, davies_bouldin_scores

    


    def plot_inertias(self,inertias):
        pass

    



