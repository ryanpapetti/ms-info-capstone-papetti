'''
Ryan Papetti

Spotify User

This script hopefully aims to control the User class that can hold playlists, etc.

'''

from playlist import Playlist
from track import Track
import datetime, pandas as pd, sqlite3, sys, datetime, numpy as np, json, pickle, os
from sqlite3 import Error
from tqdm import tqdm

from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans, AgglomerativeClustering

import seaborn as sns, matplotlib.pyplot as plt

import scipy.cluster.hierarchy as shc #making dendrograms


class SpotifyUser:
    def __init__(self, name, spotify_id, playlists = {}, contacter = None):
        '''
        The SpotifyUser instance represents a particular Spotify user denoted by a Spotify_id and allows for API communication, storage of playlists, and clustering of tracks.

        __init__(self, name, spotify_id, playlists = {}, contacter = None)

        name - a str representing the name of the user. Note it does not have to match the actual display name of the user.

        spotify_id - a str of the desired user's Spotify ID. It can be obtained from the Spotfiy account or by sharing a user and taking the last part of the URI

        playlists = {} - a dictionary of playlist ids to Playlist instances

        contacter = None - a Contacter if desired. A contacter is used to make API queries and is necessary to do so. However, all database information can be made without a contacter
        '''
        self.name = name
        self.user_id = spotify_id
        self.playlists = playlists
        self.contacter = contacter
        self.demographics = {}
        self.db_file = f"{self.name}'s ({self.user_id}) Music.db"
    
    
    @staticmethod
    def connect_to_database(database_file):
        '''
        @staticmethod
        connect_to_database(database_file)

        database_file - a str of a databsae filepath

        If the file is not found or another error occurs, the Error is raised. Otherwise a sqlite3 connection object is returned

        '''
        conn = None
        try:
            conn = sqlite3.connect(database_file)
            return conn
        except Error as e:
            raise ConnectionError(f'There was a problem: {e}')    

    def create_user_database(self):
        '''
        create_user_database(self)

        The function creates the initial database for the user. It includes three initial tables:

        1. Demographic Info - information on the user demographics (self.demographics = {} is initialized in init)

        2. Playlists - information on the user's playlists. This is an empty Dataframe here

        3. Tracks - information on the user's tracks. This starts as an empty Dataframe

        If for some reason the tables are already present, they will be replaced. 

        '''
        #the goal here is to create the necessary DataTables and database for the user to store all information!

        #first, begin by making the demo table. Assume you have demographic info
        assert self.demographics != {}
        demographic_info = pd.Series(self.demographics).to_frame().T
        
        #next, empty playlists
        playlist_columns = ['Playlist ID', 'Size', 'Name', 'Description', 'Owner', 'Snapshot ID']
        playlists_table_df = pd.DataFrame(columns = playlist_columns)

        #next empty Tracks
        tracks_table_columns = ['Track ID', 'Name', 'Album', 'Artist', 'Duration', 'Earliest Add Date']
        tracks_table_df = pd.DataFrame(columns = tracks_table_columns)

        #now make a database
        initial_db_file = self.db_file
        db_connection = SpotifyUser.connect_to_database(initial_db_file)
        #add the tables to the database

        demographic_info.to_sql(name = 'Demographic Info', con = db_connection, if_exists='replace', index = False)

        playlists_table_df.to_sql(name = 'Playlists', con = db_connection, if_exists='replace', index = False)

        tracks_table_df.to_sql(name = 'Tracks', con = db_connection, if_exists='replace', index = False)
    


    
    def get_basic_demographic_information(self):
        '''
        get_basic_demographic_information(self)

        This function retrieves the demographic information from the endpoint https://api.spotify.com/v1/users/{self.user_id}

        Currently, it assigns self.demographics in place, but really should return a dictionary of the demographic information.

        It will raise an error if the user's contacter is None.

        '''
        if self.contacter is None:
            raise AssertionError('Add a contacter!')
        link = f'https://api.spotify.com/v1/users/{self.user_id}'
        api_response = self.contacter.contact_api(link).json()
        desired_keys = ['followers', 'display_name', 'id', 'type']
        future_demos = {key: None for key in desired_keys}
        for key in future_demos:
            if key != 'followers':
                future_demos[key] = api_response[key]
            else:
                future_demos[key] = api_response[key]['total'] #special indexing for followers data
        
        self.demographics = future_demos #see docstring for future change

        return future_demos
    

    def get_all_playlist_ids(self):
        '''
        get_all_playlist_ids(self)

        This function calls https://api.spotify.com/v1/users/{self.user_id}/playlists to retrieve the playlist_id of every user playlist. I believe this only includes public playlists. If the user has over 1500 playlists, a Permission error is raised (to avoid drastic amounts of queries, but likely needs to be changed). If there is no contacter, a ValueError is raised. If over 30 queries were made. but fewer were expected, a ValueError is raised.

        This returns a set of tuples, where each tuple is of the form (playlist id, platlist name)
        '''
        if self.contacter is None:
            raise ValueError('Add a contacter!')
        link = f'https://api.spotify.com/v1/users/{self.user_id}/playlists'
        additional_q_params = {'limit': 50}
        api_response = self.contacter.contact_api(link, additional_request_parameters = additional_q_params).json()
        total = api_response['total']
        assert type(total) == int #I believe that occasionally a bad query can yield a non int total.
        final_ids = [(item['id'],item['name']) for item in api_response['items']]
        total_queries_made = 1
        while api_response['next'] and total_queries_made < 30: #call the api until you collect all playlists
            new_link = api_response['next']
            api_response = self.contacter.contact_api(new_link, additional_request_parameters = additional_q_params).json()
            final_ids.extend([(item['id'],item['name']) for item in api_response['items']])
            total_queries_made +=1
        if len(set(final_ids)) != total: #this means that too many queries were made...
            if (total / 50) > 30:
                raise PermissionError('Programmer needs to account for users with 1500 + playlists')
            raise ValueError('Too many queries were made and less than 30 should have been made...')
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
            self.playlists[playlist_id].retrieve_playlist_data(self.contacter, save_file = False)


   

    def collect_and_store_data(self): #THIS MAY BE EXPANDED UPON SIGNIFICANTLY
        '''
        collect_and_store_data(self)

        This function collects all data for the user in the following sense:

        - retrieves basic demographic information
        - creates user database
        - retrieves all playlist ids
        - populates the user's Playlists table with playlist info
        - for each playlist
            - create and populate a table in the database for the playlist
        - populates the user's track table
        - retrieves all audio features for all tracks and populates the user's Tracks table

        '''
        #assume you have NOTHING
        self.get_basic_demographic_information() #adds it to the instance variable
        self.create_user_database()
        self.get_all_playlist_information()
        db_connection = SpotifyUser.connect_to_database(self.db_file)
        self.populate_playlist_table_entirely()
        for _,playlist in self.playlists.items():
            playlist.convert_raw_track_items()
            playlist.create_playlist_table(db_connection)
        self.populate_track_table_entirely()
        self.collect_audio_features_for_all_tracks()


    def populate_playlist_table_entirely(self):
        '''
        populate_playlist_table_entirely(self)

        This function connects to the user database and populates the Playlists table with the demographic information of each Playlist instance in self.playlists. If the table already exists in the db, this REPLACES it.

        This returns None

        '''
        db_connection = SpotifyUser.connect_to_database(self.db_file)

        #assume playlists is a propagated dict
        #turn this into a dataframe --> a Playlist method 
        final_data_list = [playlist.organize_playlist_demographic_information() for _,playlist in self.playlists.items()]
        
        final_df = pd.concat(final_data_list, axis = 1).T #may need to reset index and or screw with transpose

        final_df.to_sql(name = 'Playlists', con = db_connection, if_exists = 'replace', index = False)
    


    def populate_track_table_entirely(self):
        '''
        populate_track_table_entirely(self)

        This function accomplished the following:

        - reads in the user's Playlists table to retrieve names
        - iterate through each playlist and add all track ids to a massive list
        - go through the list and remove the duplicate track ids, but uniquely only keep the earliest add date for each track
        - correct any missing data (reformat Duration column) 
        - populate user's Tracks table with the data

        If the table already exists, this will replace it.

        This returns None

        '''
        #this will assume that there is already a filled database with playlists
        db_connection = SpotifyUser.connect_to_database(self.db_file)
        #first access the playlist table
        playlists = pd.read_sql('SELECT * FROM Playlists', db_connection)
        #each playlist name is the table name to get data
        all_tracks = []
        for playlist in playlists['Name']:
            playlist_df = pd.read_sql(f'SELECT * FROM "{playlist}"', db_connection)
            playlist_tracks = [Track.create_track_from_playlist_df(playlist_df.loc[ind]) for ind in playlist_df.index]
            all_tracks.extend([track for track in playlist_tracks])
            print(f'Populating {len(playlist_tracks)} songs from {playlist}')
        
        usable_track_data = [track.retrieve_demographics() for track in all_tracks]

        track_df = pd.concat(usable_track_data, axis = 1).T
        indices_to_remove = []
        for track in track_df['Track ID']:
            track_data = track_df[track_df['Track ID'] == track].sort_values(by = 'Add Date')
            if pd.isna(track):
                indices_to_remove.extend(list(track_data.index))
            else:
                indices_to_remove.extend(list(track_data.index[1:])) #all but the first
        print(track_df.head())
        print(indices_to_remove)
        track_df.drop(indices_to_remove, axis = 'index', inplace = True)


        if track_df['Duration'].dtype == 'O':
            #convert bytes to ints; this cured a bad bug, and is likely not 100% necessary
            track_data['Duration'] = track_data['Duration'].apply(int.from_bytes, args = tuple([sys.byteorder]))

        #write to SQL
        track_df = track_df.dropna(axis = 'index').set_index('Track ID') #we have to drop NA due to songs with no track ID
        track_df.to_sql(name = 'Tracks', con = db_connection, if_exists = 'replace')

        

    
    def load_proper_table_into_df(self,table_name, sql_statement = None):
        '''
        load_proper_table_into_df(self,table_name, sql_statement = None)

        table_name - a str representing the name of the table to load into the df

        sql_statement = None - could be a str of a valid SQL statement, but as of now this is mostly unused or deprecated

        This function reads in the the requested table into a DF and modfifies certain categories if necessary. Also attempts to set the index if "Track" or "Playlist" id are available.

        Returns a dataframe

        '''
        if not sql_statement:
            sql_statement = f'SELECT * FROM "{table_name}"' #edit note: this needs to be improved for future commands that are more convoluted
        
        db_connection = SpotifyUser.connect_to_database(self.db_file)
        df = pd.read_sql(sql_statement,db_connection)

        if 'Demographic' in table_name:
            return df
        
        if 'Describe' not in table_name:

            #ID ALWAYS FIRST COL... maybe this could be better?
            id_cols = [col for col in df.columns if 'ID' in col]
            df.set_index(id_cols[0], inplace = True)

        if 'Duration' in df.columns:
            if df['Duration'].dtype == 'O':
                df['Duration'] = df['Duration'].apply(int.from_bytes, args = tuple([sys.byteorder]))
        return df
    
    def collect_audio_features_for_all_tracks(self):
        '''
        collect_audio_features_for_all_tracks(self)

        This function loads the "Tracks" table into a dataframe and retrieves the audio features for all track Ids in the dataframe.

        This also writes the data back into the SQL table for tables, replacing whatever table was there.

        Returns None

        '''
        #get all tracks
        tracks_df = self.load_proper_table_into_df('Tracks')
        print(tracks_df.head())
        track_objs = []
        for ind in tracks_df.index:
            try:
                t_obj = Track.create_track_from_track_df(tracks_df.loc[ind])
                track_objs.append(t_obj)
            except AttributeError:
                print('could not make t_obj')
                print(tracks_df.loc[ind]); raise ValueError

        print(track_objs)
        #now determine the number of bins
        bin_num = len(track_objs) // 100 + bool(len(track_objs) % 100)
        custom_bins = [i * 100 for i in range(bin_num)]
        custom_bins.append(len(track_objs))

        all_track_features = []

        query_counter = 0

        print(custom_bins)

        for i in range(len(custom_bins) - 1):
            #download i - i+1
            relevant_tracks = track_objs[custom_bins[i]: custom_bins[i+1]]
            track_ids_to_download = [track.id for track in relevant_tracks] #it is possible it does not want a list but rather a single string separated by commas
            track_ids_to_download = ','.join(track_ids_to_download)
            additional_q_params = {'ids': track_ids_to_download} 
            endpoint = 'https://api.spotify.com/v1/audio-features'
            response_obj = self.contacter.contact_api(endpoint, additional_request_parameters=additional_q_params)
            features = response_obj.json()['audio_features']
            try:
                assert len(features) == len(relevant_tracks)
            except AssertionError:
                print('LENGTHS DID NOT MATCH')
                print(features)
                print(len(features), len(relevant_tracks)); raise AssertionError

            for i,track in enumerate(relevant_tracks):
                all_track_features.append(track.parse_track_audio_features(features[i]))
            query_counter +=1
        
        print('Successfully downloaded features for {} songs in {} queries'.format(len(all_track_features), query_counter))
            
        
        tracks_w_features = pd.concat(all_track_features, axis = 1).T

        #merge the frames
        new_df = tracks_df.merge(tracks_w_features, left_index = True, right_index = True)

        db_connection = SpotifyUser.connect_to_database(self.db_file)
        #add back to SQL
        new_df.to_sql('Tracks', db_connection, if_exists = 'replace', index_label = 'Track ID') #include the index
    


    def gather_clusterable_data(self):
        '''
        gather_clusterable_data(self)

        This function gathers the necessary columns for clustering. This also turns 'Add Date' into a 0-1 range (1 being most recently added)

        Returns a new DataFrame
        '''
        tracks_df = self.load_proper_table_into_df('Tracks')
        tracks_df['Add Date'] = tracks_df['Add Date'].astype('datetime64')
        first_day = min(tracks_df['Add Date'])
        last_day = max(tracks_df['Add Date'])
        date_range = (last_day - first_day).days
        new_add_dates = [(date - first_day).days for date in tracks_df["Add Date"]]
        tracks_df['Add Date'] = new_add_dates
        tracks_df['Add Date'] /= date_range
        
        usable_cols = [col for col in tracks_df.columns if col not in ['Name', 'Artist', 'Album', 'Duration', 'time_signature', 'mode', 'key', 'Add Date']]
        return tracks_df[usable_cols]
    

    def prepare_data_for_clustering(self):
        '''
        prepare_data_for_clustering(self)

        This function gathers the necessary data for clustering, modifies both loudness and tempo (so as to prevent log errors), and scales any necessary data. 

        The function returns a numpy array of clusterable data
        '''
        usable_data = self.gather_clusterable_data().copy()
        #loudness also needs adjusting by its minimum value to make it start at 1
        usable_data['loudness'] = usable_data['loudness'] + 1 + abs(min(usable_data['loudness']))
        #tempo needs adjusting but just add 1
        usable_data['tempo'] += 1
        log2_cols = ['loudness', 'tempo']
        log10_cols = ['duration_ms']
        columns_to_scale = log2_cols + log10_cols
        already_scaled_cols = [col for col in usable_data.columns if col[0].islower() and col not in log2_cols and col not in log10_cols]

        already_scaled_data = usable_data.loc[:,already_scaled_cols]
        data_to_be_scaled = usable_data.loc[:,columns_to_scale]

        for col in data_to_be_scaled.columns:
            if col in log2_cols:
                data_to_be_scaled.loc[:,col] = data_to_be_scaled.loc[:,col].apply(np.log2)
            elif col in log10_cols:
                data_to_be_scaled.loc[:,col] = data_to_be_scaled.loc[:,col].apply(np.log10)
        
        final_data = pd.DataFrame(columns = usable_data.columns, index = usable_data.index) #use the original columns

        #Use the MinMax Scaler on the data that needs to be scaled
        scaler = MinMaxScaler()
        final_data.loc[:,columns_to_scale] = scaler.fit_transform(data_to_be_scaled.to_numpy()) #I learned here : https://stackoverflow.com/questions/24645153/pandas-dataframe-columns-scaling-with-sklearn that using to_numpy is more appropriate than values and to just reassign the columns in place

        #Finally, add the already scaled columns
        final_data.loc[:,already_scaled_cols] = already_scaled_data

        return final_data.to_numpy()
    

    def run_hierarchical_clustering(self,optimal_clusters):
        '''
        run_hierarchical_clustering(self,optimal_clusters)

        optimal_clusters - an int representing the number of clusters to pass to AgglomerativeClustering

        This function prepares data for clustering and clusters the data using AgglomerativeClustering. 

        The function returns the clusterer object

        '''
        data_for_clustering = self.prepare_data_for_clustering()
        clusterer = AgglomerativeClustering(n_clusters = optimal_clusters, affinity = 'euclidean', linkage = 'ward')
        clusterer.fit(data_for_clustering) #data must be an array!!
        return clusterer #I can get the labels from here


    


    def label_clustered_data(self, optimal_clusters):
        '''
        label_clustered_data(self, optimal_clusters)

        This function gathers the data, clusters the data, and assigns the cluster label to the proper tracks

        Returns a labelled dataframe
        '''
        usable_data = self.gather_clusterable_data().copy()
        usable_data.loc[:,'Cluster Label'] = self.run_hierarchical_clustering(optimal_clusters).labels_
        return usable_data
    

    def save_describe_labelled_track_data(self, labelled_track_data, algorithm_used = 'HC'):
        '''
        save_describe_labelled_track_data(self, labelled_track_data, algorithm_used = 'HC')

        labelled_track_data - a pandas DF

        algorithm_used = 'HC' - a string of the algorithm type

        This function saves both the described data of the cluster results and the labelled data into SQL

        Returns None

        '''
        db_connection = SpotifyUser.connect_to_database(self.db_file)
        clusters_used = max(labelled_track_data['Cluster Label']) + 1
        labels_table_name = f'{algorithm_used} {clusters_used} Labels'
        described_table_name = f'{algorithm_used} {clusters_used} Described'

        described_data = labelled_track_data.groupby('Cluster Label').mean()

        labelled_track_data.to_sql(labels_table_name, con = db_connection, if_exists = 'replace')
        described_data.to_sql(described_table_name, con = db_connection, if_exists = 'replace')

    def load_labelled_track_data(self,clusters_used,algorithm_used = 'HC'):
        '''
        load_labelled_track_data(self, clusters_used, algorithm_used = 'HC')

        clusters_used - an integer 

        algorithm_used = 'HC' - a string of the algorithm type

        This function the labelled data from the user's db into a pandas df

        Returns dataframe of labelled tracks

        '''
        _ = SpotifyUser.connect_to_database(self.db_file)
        labels_table = f'{algorithm_used} {clusters_used} Labels'
        return self.load_proper_table_into_df(labels_table)

    

    def explore_hierarchical_clustering(self):
        '''
        explore_hierarchical_clustering(self):

        This function plots the hierarchical structure of the clustered data as simply as possible

        Shows a plot to the screen, returns None
        '''
        usable_data = self.gather_clusterable_data().copy()
        hierarchical_data = shc.linkage(usable_data, method = 'ward')
        fig, ax = plt.subplots(dpi = 100)

        shc.dendrogram(hierarchical_data, ax = ax, color_threshold=0, above_threshold_color='k')
        fig.suptitle('Hierarchical Clustering of Track Data for {}'.format(self.name))
        ax.axis('off') #simple way to clean up plot

        fig.show() #no saving plots
    

    def explore_run_and_save_clustering(self):
        '''
        explore_run_and_save_clustering(self)

        This function calls explore_hierarchical_clustering with the intention of the user determining the optimal number of clusters. Once the number of clusters is specified, the data are clustered and saved into the database

        This returns None
        '''
        
        self.explore_hierarchical_clustering()

        decided_clusters = int(input('HOW MANY CLUSTERS?\n'))

        labelled_data = self.label_clustered_data(decided_clusters)
        self.save_describe_labelled_track_data(labelled_data)
    

    def find_most_typical_tracks_per_cluster(self, desired_clusters_to_explore = 'HC 8', typical_limit = 25):
        '''
        find_most_typical_tracks_per_cluster(self, desired_clusters_to_explore = 'HC 8', typical_limit = 25)

        desired_clusters_to_explore = 'HC 8' - a string representing the preamble of the desired tables inside the database

        typical_limit = 25 - an integer capping the number of songs to put into the playlist. AKA finding the {typical_limit} most typical songs in each cluster

        This function gathers all clustered from the database. For each cluster label, find the Euclidean Distance between each track and the "centroid", take the first {typical_limit} in a sorted structure, concatenate all tracks to a DataFrame, and input the frame into the database.

        Returns None

        '''
        db_connection = SpotifyUser.connect_to_database(self.db_file)
        all_tables_statement = "SELECT name FROM sqlite_master WHERE type='table';"
        result = db_connection.execute(all_tables_statement).fetchall()

        try:
            relevant_labelled_table = [table[0] for table in result if 'Label' in table[0] and table[0][:4] == desired_clusters_to_explore][0]
            relevant_described_table = [table[0] for table in result if 'Describe' in table[0] and table[0][:4] == desired_clusters_to_explore][0]
        except:
            print(result.fetchall());raise IndexError

        labelled_table = self.load_proper_table_into_df(relevant_labelled_table)
        described_table = self.load_proper_table_into_df(relevant_described_table)
        all_tracks = self.load_proper_table_into_df('Tracks') #for duplicates

        euclidean_distance_formula = lambda ser1, ser2: ((ser2 - ser1)**2).sum()

        all_distances = []

        for ind in labelled_table.index:
            cluster_label = labelled_table.loc[ind,'Cluster Label']
            comparable_data = labelled_table.loc[ind,[col for col in labelled_table.columns if col != 'Cluster Label']]
            cluster_avg = described_table.loc[cluster_label]
            all_distances.append(euclidean_distance_formula(comparable_data, cluster_avg))

        labelled_table['Distance to Centroid'] = all_distances


        final_df = []
        existing_name_artists = set() #to check for duplicates prolly an easier pandas way

        for ind in described_table.index:
            cluster_data = labelled_table[labelled_table['Cluster Label'] == ind]
            desired_indices = []
            for new_ind in cluster_data.index: #new_ind is a Track ID --> index from labelled
                name_art_pair = (all_tracks.loc[new_ind,'Name'], all_tracks.loc[new_ind,'Artist'])
                if name_art_pair not in existing_name_artists:
                    desired_indices.append(new_ind)
                    existing_name_artists.add(name_art_pair)
            cluster_data = cluster_data.loc[desired_indices]

            sorted_data = cluster_data.sort_values(by = 'Distance to Centroid').iloc[:typical_limit]
            final_df.append(sorted_data)
        
        final_df = pd.concat(final_df)

        new_table_name = f'{desired_clusters_to_explore} Most Typical Tracks'
        final_df.to_sql(new_table_name, db_connection, if_exists = 'replace')

    

    def fully_establish_and_add_cluster_playlists(self, desired_algorithm = 'HC 8'):
        '''
        fully_establish_and_add_cluster_playlists(self, desired_algorithm = 'HC 8')

        desired_algorithm = 'HC 8' - a string representing the preamble of the desired tables inside the database

        For each of the playlists created by find_most_typical_tracks_per_cluster, this function officially adds the playlist to the user's Spotify account, making it an actual playable playlist

        Returns None, but creates playlists on Spotify and updates user database

        '''
        typical_name = f'{desired_algorithm} Most Typical Tracks'
        typicals = self.load_proper_table_into_df(typical_name)
        raw_track_data = self.load_proper_table_into_df('Tracks')
        for cluster in set(typicals['Cluster Label']):
            cluster_tracks = typicals[typicals['Cluster Label'] == cluster]
            future_playlist_track_data = raw_track_data.loc[cluster_tracks.index]
            track_objs = [Track.create_track_from_track_df(future_playlist_track_data.loc[ind]) for ind in cluster_tracks.index]

            #make playlist
            playlist_params = {'name': f'HC Cluster {cluster} Typicals'}

            playlist = Playlist.generate_playlist_from_user(user = self, playlist_params = json.dumps(playlist_params))

            self.playlists[playlist.playlist_id] = playlist

            playlist.add_track_objs_to_playlist_obj(track_objs)

            playlist.add_tracks_to_spotify_playlist(user = self)

            db_connection = SpotifyUser.connect_to_database(self.db_file)

            playlist.create_playlist_table(db_connection)
            
        
        #reupdate playlists
        self.populate_playlist_table_entirely()
    

    # ========================================== NEW LISTENING HISTORY ==========================

    def retrieve_user_listening_history(self):
        if self.contacter is None:
            raise ValueError('Add a contacter!')
        link = 'https://api.spotify.com/v1/me/player/recently-played'
        additional_q_params = {'limit': 50}
        api_response = self.contacter.contact_api(link, additional_request_parameters = additional_q_params).json()


        master_listening_history_dict = {item['played_at']: Track.create_track_from_json(item) for item in api_response['items']}

        total_queries_made = 1
        while api_response['next']: #call the api until you collect all listening possible
            new_link = api_response['next']
            api_response = self.contacter.contact_api(new_link, additional_request_parameters = additional_q_params).json()
            listening_history_dict = {item['played_at']: Track.create_track_from_json(item) for item in api_response['items']}
            master_listening_history_dict.update(listening_history_dict)
            total_queries_made +=1
            print(f'On query number {total_queries_made}')
        
        print(f'There were {total_queries_made} queries made')

        
        return master_listening_history_dict

    
    def write_to_listening_history_pickle(self,listening_history):
        #this assumes you are in the right directory
        filename = f'{self.user_id} Listening History.pickle'
        file_opening = 'ab' if filename in os.listdir() else 'wb'
        with open(f'{self.user_id} Listening History.pickle', file_opening) as writer:
            pickle.dump(listening_history,writer)


    def load_user_listening_history_from_pickle(self):
        with open(f'{self.user_id} Listening History.pickle', 'rb') as reader:
            return pickle.load(reader)
        
        





    


    


        


            






















        