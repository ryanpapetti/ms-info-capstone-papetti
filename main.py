import json
from flask import Flask, request, redirect, render_template, url_for, session
import requests
from urllib.parse import quote
from flask_session import Session

from utils import prime_user_from_access_token, prepare_playlists, prepare_data, execute_clustering, gather_cluster_size_from_submission, organize_cluster_data_for_display

# Authentication Steps, paramaters, and responses are defined at https://developer.spotify.com/web-api/authorization-guide/
# Visit this url to see all the steps, parameters, and expected response.

app = Flask(__name__)

app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = 'test123test123'
Session(app)
#  Client Keys
CLIENT_ID = "7ec4038de1184e2fb0a1caf13352e295"
CLIENT_SECRET = '18fa59e0d4614c139f4c6102f5bc965a'
# AUTH_HASH = "Basic N2VjNDAzOGRlMTE4NGUyZmIwYTFjYWYxMzM1MmUyOTU6MThmYTU5ZTBkNDYxNGMxMzlmNGM2MTAyZjViYzk2NWE="

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 8095
REDIRECT_URI = "{}:{}/callback".format(CLIENT_SIDE_URL, PORT)
SCOPE = "user-read-recently-played user-top-read  playlist-modify-public playlist-modify-private user-library-modify playlist-read-private user-read-email user-read-private user-library-read playlist-read-collaborative"
# STATE = ""
# SHOW_DIALOG_bool = True
# SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "client_id": CLIENT_ID
}



@app.route("/")
def index():
    return render_template('homepage.html')

@app.route("/appeducation")
def appeducation():
    return render_template('appeducation.html')


@app.route("/authenticateuser")
def authenticateuser():
    # Auth Step 1: Authorization
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)


@app.route("/callback")
def callback():
    # Auth Step 4: Requests refresh and access tokens
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    # app.logger.info(msg=code_payload)
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)
    # Auth Step 5: Tokens are Returned to Application
    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    # refresh_token = response_data["refresh_token"]
    # token_type = response_data["token_type"]
    # expires_in = response_data["expires_in"]

    # Auth Step 6: Use the access token to access Spotify API
    authorization_header = {"Authorization": "Bearer {}".format(access_token)}
    session['VALID_AUTH_HEADER'] = authorization_header

    # Get profile data
    user_profile_api_endpoint = "{}/me".format(SPOTIFY_API_URL)
    profile_response = requests.get(user_profile_api_endpoint, headers=authorization_header)
    profile_data = json.loads(profile_response.text)
    user_id = profile_data['id']

    #make user 
    user = prime_user_from_access_token(user_id, access_token)
    session['VALID_USER'] = user
    app.logger.info(msg='Set user')
    return redirect(url_for('appeducation'))




@app.route('/clustertracks', methods=['POST'])
def clustertracks():
    algorithm = request.form.get('algorithm')
    desired_clusters = request.form.get('desired_clusters')

    app.logger.info(msg=f'algorithm: {algorithm}')
    app.logger.info(msg=f'clusters: {desired_clusters}')

    app.logger.info(msg='Auth header')
    app.logger.info(msg=f"{session['VALID_AUTH_HEADER']}")

    #gather data
    app.logger.info(msg='Preparing data')
    app.logger.info(msg=f"{session['VALID_USER']}")
    chosen_algorithm = algorithm
    chosen_clusters = gather_cluster_size_from_submission(desired_clusters)
    session['ALGORITHM_CHOSEN'] = chosen_algorithm
    session['CLUSTERING_CHOSEN'] = chosen_clusters
    
    app.logger.info(msg='cluster size determined')


    app.logger.info(msg='preparing data')
    user_prepared_data = prepare_data(session['VALID_USER'])

    app.logger.info(msg='data prepared')
    # app.logger.info(msg=user_prepared_data)



    labelled_data = execute_clustering(chosen_algorithm,chosen_clusters,user_prepared_data)

    app.logger.info(msg='data clustered')
    prepared_playlists = prepare_playlists(session['VALID_USER'],labelled_data)
    app.logger.info(msg='ready for upload')
    session['PREPARED_PLAYLISTS'] = prepared_playlists     
    app.logger.info(msg='added as session variable')
    # Combine profile and playlist data to display
    # return render_template("clusteringresults.html", stringified_playlists = json.dumps(prepared_playlists))
    return redirect(url_for('clusteringresults', _external=True))


@app.route("/clusteringresults")
def clusteringresults():
    prepared_playlists = session['PREPARED_PLAYLISTS']
    displayable_data, total_organized_playlist_data = organize_cluster_data_for_display(session['VALID_AUTH_HEADER'],prepared_playlists)
    return render_template("clusteringresults.html", displayable_data = json.dumps(displayable_data), total_organized_playlist_data = json.dumps(total_organized_playlist_data))





if __name__ == "__main__":
    app.run(debug=True, port=PORT)
