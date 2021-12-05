'''
Ryan Papetti

Spotify User

This script hopefully aims to control the User class that can hold playlists, etc.

'''
import json, logging, pandas as pd, numpy as np, matplotlib.pyplot as plt
from math import pi
from sklearn import preprocessing, metrics
from sklearn.cluster import KMeans
from scipy.cluster.hierarchy import dendrogram, linkage, cut_tree
from .playlist import Playlist
from .track import Track


class SpotifyUser:
    def __init__(self, spotify_id, playlists = {}, contacter = None, optional_display_id = ''):
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
        self.optional_display_id = optional_display_id
        np.random.seed(420)
 
    

    def get_all_user_playlist_ids(self):
        '''
        get_all_user_playlist_ids(self)

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





    
    def get_all_playlist_information(self, custom_playlist_ids = None, save_file_flag = True):
        '''
        get_all_playlist_information(self)

        Calls self.get_all_user_playlist_ids() and fills out self.playlists with the Playlist() instances

        Raises an error is self.contacter is None.

        This returns None but updates self.playlists in place

        '''

        if self.contacter is None:
            raise ValueError('Add a contacter')
        playlist_ids = self.get_all_user_playlist_ids() if custom_playlist_ids is None else custom_playlist_ids

        for playlist_info in playlist_ids:
            #make a playlist instance and add it to the user's playlist dict
            playlist_id,playlist_name = playlist_info
            self.playlists[playlist_id] = Playlist(playlist_id,playlist_name)
            self.playlists[playlist_id].retrieve_playlist_data(self.contacter, save_file = save_file_flag)





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

    

    def collect_data(self, custom_playlist_ids = None, save_file_flag = False):
        logging.info('Gathering all playlist info')
        self.get_all_playlist_information(custom_playlist_ids=custom_playlist_ids, save_file_flag=save_file_flag)
        for playlist in self.playlists.values():
            playlist.convert_raw_track_items()
        logging.info('Converted all raw track items')
        specified_tracks = self.aggregate_track_ids_across_playlists()
        aggregated_audio_features_data = self.gather_audio_features_data_from_specified_tracks(specified_tracks)
        return aggregated_audio_features_data

   

    def collect_and_store_data(self, final_storage_path, custom_playlist_ids = None): #THIS MAY BE EXPANDED UPON SIGNIFICANTLY
        '''
        collect_and_store_data(self)

        This function collects all data for the user in the following sense:

        - creates user database
        - retrieves all playlist ids
        - populates the user's playlist info

        - retrieves all audio features for all tracks
        '''
        aggregated_audio_features_data = self.collect_data(custom_playlist_ids)

        self.save_audio_features_data(aggregated_audio_features_data,final_storage_path)


    

    def prepare_data_for_clustering(self,aggregated_audio_features_data, alternative_features=None):
        aggregated_audio_features_data_copy = aggregated_audio_features_data.copy()
        
        if alternative_features is None:
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
    def kmeans_cluster_data(normalized_data, initialized_model):
        initialized_model.fit(normalized_data)
        return initialized_model


    @staticmethod
    def evaluate_kmeans_clusterings(normalized_data):
        inertias = []
        davies_bouldin_scores = []

        for k in range(2, 26):
            model = KMeans(n_clusters=k)
            model.fit(normalized_data) #fit/train the model
            labels = model.labels_
            davies_bouldin_scores.append(metrics.davies_bouldin_score(normalized_data, labels))
            inertias.append(model.inertia_)
    
        return inertias, davies_bouldin_scores


    @staticmethod
    def produce_linkage_matrix(normalized_data):
        return linkage(normalized_data,method='ward')
    


    def plot_inertias_db_scores(self,inertias, db_scores):
        fig, axes = plt.subplots(ncols=2)
        left_ax,right_ax = axes

        left_ax.plot(inertias)
        left_ax.set_title('Inertia')

        right_ax.plot(db_scores)
        right_ax.set_title('Davies Bouldin Score')
        proper_id = self.user_id if not self.optional_display_id else self.optional_display_id 
        fig.savefig(f'../results/{proper_id}inertia_dbscore.png', bbox_inches = 'tight', dpi=300)

    

    def plot_dendrogram(self,linked_data):
        fig,ax = plt.subplots()
        proper_id = self.user_id if not self.optional_display_id else self.optional_display_id 
        dn = dendrogram(linked_data, ax = ax, no_labels = True, above_threshold_color='black', color_threshold=0)
        ax.set_title(f'Cluster Dendrogram for {proper_id} Tracks', y = 1.05)
        fig.savefig(f'../results/{proper_id}_dendrogram.png', bbox_inches='tight', dpi = 500)

    @staticmethod
    def organize_by_centroid_distance(labelled_cluster_data):
        cluster_data_centroids = SpotifyUser.collect_centroids(labelled_cluster_data)
        euclidean_distance_formula = lambda ser1, ser2: ((ser2 - ser1)**2).sum()
        centroid_distances = []
        for _, track_data in labelled_cluster_data.iterrows():
            cluster_label = track_data['Label']
            cluster_centroid = cluster_data_centroids.loc[cluster_label]
            relevant_data = track_data.drop(['Label'])
            calculated_distance = euclidean_distance_formula(relevant_data,cluster_centroid)
            centroid_distances.append(calculated_distance)
        labelled_cluster_data.loc[:,'Distance to Centroid'] = centroid_distances
        return labelled_cluster_data.sort_values(by='Distance to Centroid')


    @staticmethod
    def collect_centroids(labelled_cluster_data):
        return labelled_cluster_data.groupby('Label').mean()



    def create_centroid_ax(self,centroid,ax):
        assert isinstance(centroid,pd.Series)
        plottable_features = [
            "danceability",
            "energy",
            "valence",
            "acousticness",
            "instrumentalness"]
        centroid = centroid[plottable_features]
        ax_title = f'Centroid Chart for Cluster {centroid.name}'
        num_variables = len(centroid)
        plottable_values = list(centroid.values)
        plottable_values.append(plottable_values[0])
        angles = [n/float(num_variables) * 2 * pi for n in range(num_variables)]
        angles.append(angles[0])
        #ax.set_xticks(angles[:-1],centroid.index,color = 'grey', size = 8)
        ax.set_xticks(angles[:-1])

        labels = [val[0] for val in centroid.index]

        ax.set_xticklabels(labels, color = 'grey', size = 4.5)
        ax.set_rlabel_position(0)
        ax.set_yticks([])
        ax.set_yticklabels([], size = 8, color = 'grey')
        ax.tick_params(axis = 'both', which = 'both', color = 'grey', pad = -5.5)
        # old_title = 'Cluster ' + str(centroid.name)
        ax.set_title(ax_title, size = 'xx-small', pad = 10) #got rid of + 1
        # ax.set_ylim(0,0.45) #to see some of the smaller trends

        centroid_color = (centroid['danceability'], centroid['energy'], centroid['valence'])

        ax.plot(angles,plottable_values, linewidth=1, linestyle='solid', color = centroid_color)
        ax.fill(angles, plottable_values, color = centroid_color, alpha=0.6)
        return ax

    def visualize_cluster_centroids_data(self, centroid_df, algorithm = 'Agglomerative', save_plot = True):
        plottable_data = centroid_df.copy()
        cluster_num = len(plottable_data.index)
        logging.info('Finding size of clusters')

        #now I need to find the number of plots to make. The answer is the same as the number of clusters
        rows = cluster_num // 2 + bool(cluster_num % 2)
        logging.info(f'Found number of rows: {rows}')
        logging.info('Attempting to create subplots')
        fig, axes = plt.subplots(rows,2, subplot_kw={'projection': 'polar'}, dpi = 1000)

        #I want each axes to plot the proper plot. There is no natural order. Cycle through each axes and plot only one row worth of data at a time
        #the packaging of axes makes enumerate not feasible
        cluster_to_plot = 0
        for sub_ax in axes:
            #each ax here is a collect
            for ax in sub_ax:
                try:
                    data = plottable_data.iloc[cluster_to_plot]
                    ax = self.create_centroid_ax(data,ax) #change to have kwargs
                    cluster_to_plot += 1
                except IndexError:
                
                    ax.set_axis_off()
                #I decided to incorporate a makeshift legend and add bottom text
                #make a list of the text 
                #legend_text = 'Key:\n\nA: Applied Medicinal\nF: Flower\nV: Vape\nC: Concentrate\nE: Edible\nP: Preroll'
                #now add the text
                #ax.text(0.2,0.63,s=legend_text, transform = ax.transAxes, fontsize = 6, color = 'black', verticalalignment = 'center', horizontalalignment = 'left')

                #add bottom text
                # bottom_text = 'Created by Ryan Papetti for 4Front Ventures'
                # ax.text(-0.3,-0.3,s = bottom_text, transform = ax.transAxes, fontsize = 4, color = 'gray')


        #fig.tight_layout(pad = 1.3)
        appropriate_label = self.user_id if not self.optional_display_id else self.optional_display_id
        fig.tight_layout(rect=[0, 0.03, 1, 0.95]) #attempt to make space
        fig.suptitle('Audio Features Centroids of {} Using {} On {} Clusters'.format(appropriate_label,algorithm,cluster_num), size = 11)

        if save_plot:
            fig.savefig('../results/Audio Features Centroids of {} Using {} On {} Clusters.png'.format(appropriate_label,algorithm,cluster_num), bbox_inches = 'tight', dpi = 1000)

        #kwargs?


    def generate_uploadable_playlists(self, labelled_data):
        uploadable_playlists = {}

        for label in set(labelled_data['Label']):
            cluster_data = SpotifyUser.organize_by_centroid_distance(labelled_data[labelled_data['Label'] == label])
            uploadable_playlists[label] = list(cluster_data.index)

        return uploadable_playlists






    def deploy_single_cluster_playlist(self,tracks_to_deploy,cluster_id,cluster_algo):
        if self.name is not None:
                id_to_add = self.name
        else:
            id_to_add = self.user_id if not self.optional_display_id else self.optional_display_id
        new_name = f"{id_to_add}'s {cluster_algo} Cluster {cluster_id}"
        playlist_params = {'name':new_name, 'description': 'These are tracks organized by their distance to the cluster centroid. The higher the song appears on this playlist, the more typical it is for this cluster. What can you find? Created via Radial Web App by Ryan Papetti'}
        associated_tracks = tracks_to_deploy
        associated_tracks_objs = [Track(track_id) for track_id in associated_tracks]

        playlist = Playlist.generate_playlist_from_user(user = self, playlist_params = json.dumps(playlist_params))

        # playlist.update_playlist_metadata(self, playlist_params)

        playlist.add_track_objs_to_playlist_obj(associated_tracks_objs)

        playlist.add_tracks_to_spotify_playlist(user = self)
        return playlist




    def add_cluster_playlists(self, cluster_playlists, cluster_algo = 'KMeans'):
        '''
        fully_establish_and_add_cluster_playlists(self, desired_algorithm = 'HC 8')

        desired_algorithm = 'HC 8' - a string representing the preamble of the desired tables inside the database

        For each of the playlists created by find_most_typical_tracks_per_cluster, this function officially adds the playlist to the user's Spotify account, making it an actual playable playlist

        Returns None, but creates playlists on Spotify and updates user database

        '''

        for cluster_id, cluster_playlist in cluster_playlists.items():
            _ = self.deploy_single_cluster_playlist(cluster_playlist, cluster_id + 1,cluster_algo)


        

