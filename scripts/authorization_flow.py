import urllib, requests, json, time, logging

def read_credentials():
    with open('../credentials/application_credentials.txt') as reader:
        client_id, client_secret = (line.strip() for line in reader)
    return client_id, client_secret


def read_auth_hash():
    with open('../credentials/auth_hash.txt') as reader:
        authorization_hash = ''.join([line.strip() for line in reader])
    return authorization_hash 


def geturl(client_id):
    '''
    Input:
        client_id : string containing client id
        redirect_uri : string containing redirect uri
        scope : string with all necessary scopes separated by spaces
    Output:
        None
    -------------------
    Task:
        1. url = https://accounts.spotify.com/authorize?client_id=<YOUR CLIENT ID>&redirect_uri=<YOUR REDIRECT URI>&response_type=code&scope=<YOUR SCOPES>
        2. print url with correct information
    '''

    redirect_uri = 'http://localhost/callback' #this must be the same in your Spotify app

    scope = 'ugc-image-upload user-read-recently-played user-read-playback-state user-top-read app-remote-control playlist-modify-public user-modify-playback-state playlist-modify-private user-follow-modify user-read-currently-playing user-follow-read user-library-modify user-read-playback-position playlist-read-private user-read-email user-read-private user-library-read playlist-read-collaborative streaming' #it's likely not all scopes are needed. Tutorials recommend all for  now
    
    url = f'https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={urllib.parse.quote(redirect_uri)}&scope={urllib.parse.quote(scope)}'

    print(url)
    return url

def refreshTheToken(refreshToken, auth_hash):

    clientIdClientSecret = f'Basic {auth_hash}'
    print(clientIdClientSecret)
    data = {'grant_type': 'refresh_token', 'refresh_token': refreshToken}


    headers = {'Authorization': clientIdClientSecret}

    p = requests.post('https://accounts.spotify.com/api/token', data=data, headers=headers)

    spotifyToken = p.json()
    print(spotifyToken)

    # Place the expiration time (current time + almost an hour), and access token into the json
    spotifyState = {'spotify': 'prod', 'expiresAt': int(time.time()) + 3200, 'accessToken': spotifyToken['access_token']}
    with open('../credentials/spotifystate.json', 'w') as f:
        json.dump(spotifyState, f)




def getAccessToken(refreshToken, auth_hash):
    refreshTheToken(refreshToken, auth_hash)
    with open('../credentials/spotifystate.json') as f:
          spotifyState = json.load(f)
    return spotifyState['accessToken']







def main():
    client_id, client_secret = read_credentials()

    auth_hash = read_auth_hash()

    # url = geturl(client_id)

    #now get og access token and dump into file

    getAccessToken('AQAEriHyJqE4DiIyrMiTi8OiYgVZNwbAo1eA5ye8f9ulaQZlJudmk2FVwdfSHcGZQbUXLTcH920YQlK4uWWOMJNOQ2sB0cgOW6Gc-WMUv4p87AZ8mIBm47JbLkBHuGhkthU', auth_hash)
    # getAccessToken('123', auth_hash)



if __name__ == '__main__':
    main()