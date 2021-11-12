import json
from flask import Flask, request, redirect, render_template
import requests
from urllib.parse import quote

from scripts import SpotifyUser, Contacter
from utils import prime_user_from_access_token, prepare_playlists, prepare_data, execute_clustering

# Authentication Steps, paramaters, and responses are defined at https://developer.spotify.com/web-api/authorization-guide/
# Visit this url to see all the steps, parameters, and expected response.


app = Flask(__name__)

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
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    # "state": STATE,
    # "show_dialog": SHOW_DIALOG_str,
    "client_id": CLIENT_ID
}


@app.route("/")
def index():
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
    print(code_payload)
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)
    print(post_request.status_code)
    # Auth Step 5: Tokens are Returned to Application
    response_data = json.loads(post_request.text)
    print(response_data)
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]

    # Auth Step 6: Use the access token to access Spotify API
    authorization_header = {"Authorization": "Bearer {}".format(access_token)}


    #THIS IS WHERE THINGS COULD AND SHOULD BE UPDATED FOR FLASK


    # Get profile data
    user_profile_api_endpoint = "{}/me".format(SPOTIFY_API_URL)
    profile_response = requests.get(user_profile_api_endpoint, headers=authorization_header)
    profile_data = json.loads(profile_response.text)
    user_id = profile_data['id']

    #make user 
    user = prime_user_from_access_token(user_id, access_token)

    #gather data
    user_prepared_data = prepare_data(user)

    #THIS IS WHERE I NEED TO GATHER THE USER'S PREFERENCES SOMEHOW. I WILL HARDCODE FOR NOW

    chosen_algorithm = 'kmeans'
    chosen_clusters = 5


    labelled_data = execute_clustering(chosen_algorithm,chosen_clusters,user_prepared_data)
    prepared_playlists = prepare_playlists(user,labelled_data)     


    # Get user playlist data
    playlist_api_endpoint = "{}/playlists".format(profile_data["href"])
    playlists_response = requests.get(playlist_api_endpoint, headers=authorization_header)
    playlist_data = json.loads(playlists_response.text)

    # Combine profile and playlist data to display
    display_arr = playlist_data['items']
    return render_template("index.html", sorted_array=display_arr, stringified_playlists = json.dumps(prepared_playlists))


if __name__ == "__main__":
    app.run(debug=True, port=PORT)
