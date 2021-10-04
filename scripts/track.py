'''
Ryan Papetti

track.py

This defines the class and behaviors for the Track object aka each song

'''
import logging
class Track:
    def __init__(self,track_id = None, album = None, artist = None, duration = None,name = None, added_at = None):
        self.id = track_id
        self.album = album
        self.artist = artist
        self.duration = duration #write static method to turn duration (ms) into minutes/seconds if applicable
        self.name = name
        self.added = added_at

    def __eq__(self,other):
        return self.id == other.id

    @classmethod
    def create_track_from_json(cls,track_json):
        try:
            track_data = track_json['track']
            added_time = track_json.get('added_at')        
            #I need to break apart the artist/album and make the artist class as well as find a way to save this
            track_id = track_data['id']
            # album = track_data['album']['name'] if 'album' in track_data else None
            # artist = track_data['artists'][0]['name'] #the first artist
            duration = track_data['duration_ms']
            # name = track_data['name']
        
        except:
            logging.log(track_json)
            raise ValueError

        return cls(track_id = track_id, duration = duration,  added_at = added_time)


    def retrieve_track_audio_features(self,contacter):
        '''
        RETEST AND REWRITE TO MAKE SUITABLE FOR NEW CLASS
        '''
        
        audio_analysis_link = 'https://api.spotify.com/v1/audio-features/{}'.format(self.id)

        features_response = contacter.contact_api(audio_analysis_link)

        audio_features_json = features_response.json()

        unimportant_keys = ['uri', 'track_href', 'analysis_url' 'time_signature', 'analysis_url']

        cleaned_raw_data = {key: audio_features_json[key] for key in audio_features_json if key not in unimportant_keys}

        return cleaned_raw_data
