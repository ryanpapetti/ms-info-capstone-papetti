'''
Ryan Papetti
Spotify Analysis
Downloading all songs from my playlists
January 27, 2020 RIP Kobe
'''

from playlist import Playlist
from api_contacter import Contacter
from spotify_user import SpotifyUser
import os


def create_contacter():
    credentials = '../Docs/json_keys.txt'
    return Contacter.read_in_credentials(credentials)

def establish_user(name,user_id, contacter = None):
    return SpotifyUser(name = name, spotify_id = user_id, contacter= contacter)


def update_tracks_table_and_check(spotify_user):
    spotify_user.populate_track_table_entirely()
    spotify_user.collect_audio_features_for_all_tracks()
    return spotify_user.load_proper_table_into_df('Tracks')


def main():
    # contacter = create_contacter()
    contacter = None #for quick debugging.....
    user = establish_user('Ryan Henry Papetti','1232063482', contacter) 
    os.chdir('../Data')

    # listening_history = user.retrieve_user_listening_history()
    
    # user.collect_and_store_data()
    # _ = update_tracks_table_and_check(user)    
    
    user.explore_run_and_save_clustering()

    clusters_used = input('CLUSTERS?\n')
    user.find_most_typical_tracks_per_cluster(f'HC {clusters_used}')
    # user.fully_establish_and_add_cluster_playlists(f'HC {clusters_used}')

if __name__ == "__main__":
    main()