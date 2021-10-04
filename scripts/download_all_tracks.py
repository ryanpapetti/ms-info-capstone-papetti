import requests, pandas as pd

def get_playlist_ids(headers):
    response = requests.get(f'https://api.spotify.com/v1/me/playlists', headers=headers)
    message = response.json()
    payload = message['items']
    return set([playlist['id'] for playlist in payload])


def get_track_ids(tracks):
    ids = set()
    for track in tracks:
        ids.add(track['track']['id'])

    return ','.join(ids)




def get_playlist_data(playlist_id, headers):
    session = requests.Session()

    playlist = session.get(f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headers).json()
    tracks = playlist['tracks']['items']
    

    response = session.get(f'https://api.spotify.com/v1/audio-features?ids={get_track_ids(tracks)}', headers=headers)
    data = response.json()['audio_features']

    next_url = playlist['tracks']['next']

    while next_url:
        playlist = session.get(next_url, headers=headers).json()
        tracks = playlist['items']

        response = session.get(f'https://api.spotify.com/v1/audio-features?ids={get_track_ids(tracks)}', headers=headers)
        data += response.json()['audio_features']

        next_url = playlist['next']

    df = pd.DataFrame(data)

    return df




def main():

    my_playlist_id = "" #put playlist ID here

    df = get_playlist_data(my_playlist_id) # get the data

    #get features
    features = [
        "danceability",
        "energy",
        "loudness",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "tempo",
        "duration_ms"]
    df = df[features]


if __name__ == '__main__':
    main()



