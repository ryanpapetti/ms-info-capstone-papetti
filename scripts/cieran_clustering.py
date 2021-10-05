
import logging
from sklearn.cluster import KMeans

from new_user import SpotifyUser
from api_contacter import Contacter 

import json


def main():
    logging.basicConfig(filename='../logs/cieran_upload.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')
    og_audio_features = json.load(open('../data/1232063482_tracks.json'))

    ryan_user_id = '1232063482'
    ryan_contacter = Contacter()
    ryan_contacter.gather_auth_hash('../credentials/auth_hash.txt')
    ryan_contacter.prime_auth_header()
    ryan_contacter.refreshTheToken('AQAEriHyJqE4DiIyrMiTi8OiYgVZNwbAo1eA5ye8f9ulaQZlJudmk2FVwdfSHcGZQbUXLTcH920YQlK4uWWOMJNOQ2sB0cgOW6Gc-WMUv4p87AZ8mIBm47JbLkBHuGhkthU')
    ryan_user = SpotifyUser(ryan_user_id, contacter=ryan_contacter)

    logging.info('Beginning clustering')

    ryan_prepped_data = ryan_user.prepare_data_for_clustering(og_audio_features)

    normalized_data = SpotifyUser.normalize_prepped_data(ryan_prepped_data)

    clusterer = SpotifyUser.cluster_data(normalized_data,KMeans(10))

    labelled_data = ryan_prepped_data.copy()

    labelled_data['Label'] = clusterer.labels_

    uploadable_playlists = ryan_user.generate_uploadable_playlists(labelled_data)

    ryan_user.add_cluster_playlists(uploadable_playlists)










if __name__ == '__main__':
    main()


