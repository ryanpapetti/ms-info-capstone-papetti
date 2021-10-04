import logging, time
from new_user import SpotifyUser
from api_contacter import Contacter

def main():
    logging.basicConfig(filename='../logs/ryan_data_collection.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')
    ryan_user_id = '1232063482'
    ryan_contacter = Contacter()
    ryan_contacter.gather_auth_hash('../credentials/auth_hash.txt')
    ryan_contacter.prime_auth_header()
    ryan_contacter.refreshTheToken('AQAEriHyJqE4DiIyrMiTi8OiYgVZNwbAo1eA5ye8f9ulaQZlJudmk2FVwdfSHcGZQbUXLTcH920YQlK4uWWOMJNOQ2sB0cgOW6Gc-WMUv4p87AZ8mIBm47JbLkBHuGhkthU')
    ryan_user = SpotifyUser(ryan_user_id, contacter=ryan_contacter)
    logging.info('Timing how long data collection and storing takes')
    start_time = time.time()
    ryan_user.collect_and_store_data(f'../data/{ryan_user_id}_tracks.json')
    logging.info(f'The elapsed time is {time.time() - start_time} seconds')




if __name__ =='__main__':
    main()