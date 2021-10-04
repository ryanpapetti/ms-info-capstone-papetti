'''
Ryan Papetti

Spotify User

This script hopefully aims to control the User class that can hold playlists, etc.

'''
import json, logging
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
        logging.info('Working on hitting the endpoint')
        link = f'https://api.spotify.com/v1/users/{self.user_id}/playlists'
        api_response = self.contacter.contact_api(link).json()
        total = api_response['total']
        assert type(total) == int #I believe that occasionally a bad query can yield a non int total.
        final_ids = [(item['id'],item['name']) for item in api_response['items']]
        total_queries_made = 1
        while api_response['next'] and total_queries_made < 30: #call the api until you collect all playlists
            new_link = api_response['next']
            api_response = self.contacter.contact_api(new_link).json()
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


    


