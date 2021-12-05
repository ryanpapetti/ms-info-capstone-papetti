import json, logging
from .track import Track

class Playlist:
    def __init__(self, playlist_id, name, owner = None, description = None, snapshot_id = None):
        self.playlist_id = playlist_id
        self.name = name
        self.playlist_size = None
        self.raw_playlist_items = []
        self.owner = owner
        self.description = description
        self.snapshot_id = snapshot_id
        self.tracks = [] #I think this may need to be changed to a dict, but if it works...
    
    def __eq__(self,other):
        return self.playlist_id == other.playlist_id
    
    @classmethod
    def generate_playlist_from_user(cls,user, playlist_params):
        endpoint = f'https://api.spotify.com/v1/users/{user.user_id}/playlists' #it is a POST request
        logging.info(f'Generating playlist with params: {json.dumps(playlist_params)}')
        response_json = user.contacter.contact_api(endpoint, data_params = playlist_params, contact_type = 'post').json()

        description = response_json['description']
        playlist_id = response_json['id']
        name = response_json['name']
        snapshot_id = response_json['snapshot_id']
        owner = response_json['owner']['display_name']
    
        #make playlist()
        return cls(playlist_id,name,owner,description,snapshot_id)

    

    def retrieve_playlist_data(self,contacter, save_file = True):
        spotify_playlist_link = 'https://api.spotify.com/v1/playlists/{}'.format(self.playlist_id)
        
        playlist_response = contacter.contact_api(spotify_playlist_link)
        
        playlist_json = playlist_response.json()

        track_data = playlist_json['tracks']

        self.playlist_size = int(track_data['total'])
        self.raw_playlist_items.extend(track_data['items'])
        user_data = playlist_json['owner']
        self.description = playlist_json['description']
        self.owner = user_data['display_name']
        self.snapshot_id = playlist_json['snapshot_id']

        #now, while playlist_json['next'] exists. make a checker to make sure we did not hit an infinite loop
        total_queries_made = 1
        logging.info(f'Working with {self.name}')
        while track_data['next']:
            new_response = contacter.contact_api(track_data['next'])
            try:
                track_data = new_response.json()
                self.raw_playlist_items.extend(track_data['items'])
            except:
                logging.info(track_data)
                logging.info(track_data)
                logging.info(track_data.keys())
                raise ValueError('Unable to extend track_data')
            total_queries_made +=1
        logging.info('Successfully downloaded data for {} after {} queries'.format(self.name, total_queries_made))

        if save_file:
            self.write_playlist_items()
        
        

    def write_playlist_items(self):
        with open('../data/{} Raw Track Items.json'.format(self.playlist_id), 'w') as writer:
            json.dump(self.raw_playlist_items,writer)
    
    def add_track_objs_to_playlist_obj(self, items):
        self.tracks.extend(items)
    

    def organize_playlist_demographic_information(self):        
        organized_data = {}

        organized_data['Playlist ID'] = self.playlist_id
        organized_data['Size'] = len(self.tracks)
        organized_data['Name'] = self.name
        organized_data['Description'] = self.description
        organized_data['Owner'] = self.owner
        organized_data['Snapshot ID'] = self.snapshot_id

        return organized_data
    
    def convert_raw_track_items(self):
        assert self.raw_playlist_items
        #goal is to Track() all items and make a new instance variable
        self.tracks = [Track.create_track_from_json(item) for item in self.raw_playlist_items]
    

    
    def add_tracks_to_spotify_playlist(self,user):
        assert self.tracks
        track_objs = self.tracks

        bin_num = len(track_objs) // 100 + bool(len(track_objs) % 100)
        custom_bins = [i * 100 for i in range(bin_num)]
        custom_bins.append(len(track_objs))
        
        query_counter = 0

        for i in range(len(custom_bins) - 1):
            #download i - i+1
            relevant_tracks = track_objs[custom_bins[i]: custom_bins[i+1]]
            track_uris_to_add = [f'spotify:track:{track.id}' for track in relevant_tracks] #it is possible it does not want a list but rather a single string separated by commas; it may depend on the function
            body_params = json.dumps({'uris': track_uris_to_add})
            endpoint = f'https://api.spotify.com/v1/playlists/{self.playlist_id}/tracks'
            try:
                response_json = user.contacter.contact_api(endpoint, data_params = body_params, contact_type = 'post').json()
            except:
                logging.info(response_json.json())
                raise ValueError
            
            #update snapshot ID
            # response = user.contacter.contact_api(endpoint, data_params = body_params, contact_type = 'post').json() #adds songs

            self.snapshot_id = response_json['snapshot_id']
            query_counter +=1
        logging.info('Successfully added {} tracks to {} for {} in {} queries'.format(len(track_objs), self.name, user.name , query_counter))


    def update_playlist_metadata(self,user, metadata_to_update):
        uploadable_metadata = json.dumps(metadata_to_update)
        endpoint = f'https://api.spotify.com/v1/playlists/{self.playlist_id}'
        try:
            response_json = user.contacter.contact_api(endpoint, data_params = uploadable_metadata, contact_type = 'put').json()
            logging.info(response_json)
            return True
        except:
            logging.info('There was an error with the request')
            raise ValueError








