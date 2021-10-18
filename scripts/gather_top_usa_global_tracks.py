import logging, time
from new_user import SpotifyUser
from api_contacter import Contacter


def gather_custom_tracks(desired_user_id,desired_playlist_ids_names):
    desired_user_contacter = Contacter()
    desired_user_contacter.gather_auth_hash('../credentials/auth_hash.txt')
    desired_user_contacter.prime_auth_header()
    desired_user_contacter.refreshTheToken('AQAEriHyJqE4DiIyrMiTi8OiYgVZNwbAo1eA5ye8f9ulaQZlJudmk2FVwdfSHcGZQbUXLTcH920YQlK4uWWOMJNOQ2sB0cgOW6Gc-WMUv4p87AZ8mIBm47JbLkBHuGhkthU')
    desired_user_user = SpotifyUser(desired_user_id, contacter=desired_user_contacter)
    logging.info('Timing how long data collection and storing takes')
    start_time = time.time()
    desired_user_user.collect_and_store_data(f'../data/{desired_user_id}_tracks.json',desired_playlist_ids_names)
    logging.info(f'The elapsed time is {time.time() - start_time} seconds')





def main():
    logging.basicConfig(filename='../logs/custom_tracks_data_collection.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')

    top_50_custom_id = 'Top Hits Oct 17 2021'
    top_50_playlist_ids = {('37i9dQZEVXbLp5XoPON0wI', 'Top 50 USA Oct 17 2021'), ('37i9dQZEVXbNG2KDcFcKOF', 'Top 50 Global Oct 17 2021')}
    
    gather_custom_tracks(top_50_custom_id,top_50_playlist_ids)




if __name__ == '__main__':
    main()


