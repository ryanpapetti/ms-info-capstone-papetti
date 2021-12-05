
import requests, json, time, logging, os

class Contacter:
    def __init__(self, auth_hash = None, accessToken = None): #IF DEPRECATED, CONTACTER MAY BE ACCESS TOKEN UNIQUE

        self.session = requests.session()
        self.auth_hash = None 
        self.auth_header = None

        self.accessToken = None
        self.accessHeader = None



    def prime_auth_header(self):
        assert self.auth_hash
        self.auth_header = {'Authorization': 'Basic ' + self.auth_hash} #needs to have this format
        
    def gather_auth_hash(self, filepath):
        logging.info(f'Passed filepath: {filepath}')
        if filepath.upper() != 'ENVIRONMENT':
            try:
                with open(filepath) as reader:
                    authorization_hash = reader.readline().strip()
                self.auth_hash = authorization_hash 
            except FileNotFoundError:
                raise FileNotFoundError('We cannot find the auth hash file. You may need to run the bash script first')
        else:
            self.auth_header = os.environ.get('AUTH_HASH')



    def formAccessHeaderfromToken(self, passable_token):
        if not passable_token:
            assert self.accessToken
            self.accessHeader = {'Authorization': f'Bearer {self.accessToken}'}
        else:
            self.accessHeader = {'Authorization': f'Bearer {passable_token}'}


    def refreshTheToken(self,refreshToken, dump_filepath = None):
        assert self.auth_header
        logging.info(self.auth_header)
        
        data = {'grant_type': 'refresh_token', 'refresh_token': refreshToken}


        headers = self.auth_header.copy()

        response = self.session.post('https://accounts.spotify.com/api/token', data=data, headers=headers)

        spotifyToken = response.json()

        logging.info(spotifyToken)

        # Place the expiration time (current time + almost an hour), and access token into the json
        spotifyState = {'spotify': 'prod', 'expiresAt': int(time.time()) + 3200, 'accessToken': spotifyToken['access_token']}



        if dump_filepath is not None:
            with open(dump_filepath, 'w') as writer:
                json.dump(spotifyState, writer)
        self.accessToken = spotifyState['accessToken']
        self.formAccessHeaderfromToken()
    

    def contact_api(self, endpoint, additional_request_parameters = None, contact_type = 'get', data_params = None):
        assert self.accessHeader
        
        function_caller = {'get': self.session.get, 'post': self.session.post, 'put': self.session.put}
        proper_func = function_caller[contact_type]

        logging.info(f'We are making a {contact_type.upper()} request to {endpoint}')

        if contact_type in ['post', 'put']:
            new_auth_header = self.accessHeader
            new_auth_header['Content-Type'] = 'application/json'
            logging.info(f'Proceeding with {contact_type.upper()} request')
            response =  proper_func(endpoint, headers = new_auth_header, data = data_params)
        else:
            logging.info('Proceeding with GET request')
            response =  proper_func(endpoint, headers = self.accessHeader, params = additional_request_parameters)
        
        try:
            assert response.status_code // 100 == 2
            logging.info('Successful request')
            return response
        except AssertionError:
            logging.info('Unsuccessful request')
            logging.info(response.status_code)
            logging.info(response.text)
            raise AssertionError(f'There was an unsuccessful request using {endpoint}')

        
        
        
    
    @staticmethod
    def query_counter(total,limit = 100):
        #here the total is the number of items in the playlist (or user's set of playlists)
        return total // limit + 1 if total != limit else 1



    
