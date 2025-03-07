from flask import Flask, redirect, request, session, url_for, render_template
import requests
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure random key

# Your Spotify application credentials
CLIENT_ID = 'a61630d5ce474d0cb89504a3b9db1b4b'
CLIENT_SECRET = '2719c0085bca43e9b64a98cccf19c094'
REDIRECT_URI = 'http://localhost:5000/callback'  # Change this for deployment
SCOPE = 'playlist-read-private user-read-email user-follow-modify user-follow-read playlist-modify-public playlist-read-collaborative playlist-modify-private user-read-private'
MY_SPOTIFY_USER_ID = 'q5hv21z6c8gmz5jgnnyzmb9xw'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    auth_url = (
        'https://accounts.spotify.com/authorize?'
        f'client_id={CLIENT_ID}&'
        f'redirect_uri={REDIRECT_URI}&'
        f'scope={SCOPE}&'
        'response_type=code'
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "No code provided. Authentication failed.", 400

    # Exchange the authorization code for an access token
    token_url = 'https://accounts.spotify.com/api/token'
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    response = requests.post(token_url, data=token_data)

    if response.ok:
        access_token = response.json().get('access_token')
        session['access_token'] = access_token

        user_info = save_user_data(access_token)
        if user_info:
            session['user_id'] = user_info['id']
            follow_my_account(access_token)  # Automatically follow your Spotify account
            return redirect(url_for('view_playlists'))
        else:
            return "Failed to retrieve user data.", 400
    else:
        return "Error retrieving access token.", 400

def save_user_data(access_token):
    user_info_url = 'https://api.spotify.com/v1/me'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    user_info_response = requests.get(user_info_url, headers=headers)
    
    if user_info_response.ok:
        user_info = user_info_response.json()
        
        # Get the current time in Germany
        timezone = pytz.timezone('Europe/Berlin')
        login_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")
        
        # Save user info to data.txt including login time
        if save_to_file(user_info, login_time):
            print(f"User data saved for {user_info.get('display_name')}.")
        else:
            print("Failed to save user data.")

        return {
            'id': user_info.get('id'),
            'email': user_info.get('email'),
            'display_name': user_info.get('display_name')
        }
    else:
        print("Failed to fetch user info from Spotify.")
        return None

def save_to_file(user_info, login_time):
    try:
        with open("data.txt", "a") as file:
            file.write(f"Username: {user_info.get('display_name')}\n")
            file.write(f"Email: {user_info.get('email')}\n")
            file.write(f"User ID: {user_info.get('id')}\n")
            file.write(f"Login Time (Germany): {login_time}\n")
            file.write("-" * 20 + "\n")
        return True
    except Exception as e:
        print(f"Error writing to file: {e}")
        return False

def follow_my_account(access_token):
    follow_url = f'https://api.spotify.com/v1/me/following?type=user&ids={MY_SPOTIFY_USER_ID}'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.put(follow_url, headers=headers)
    if response.ok:
        print("Successfully followed the account.")
    else:
        print("Failed to follow the account:", response.text)

@app.route('/playlists')
def view_playlists():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    playlists = get_user_playlists(session['access_token'])
    return render_template('playlist.html', playlists=playlists)

def get_user_playlists(access_token):
    playlists_url = 'https://api.spotify.com/v1/me/playlists'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(playlists_url, headers=headers)
    
    if response.ok:
        return response.json().get('items', [])
    else:
        print("Failed to fetch playlists.")
        return []

@app.route('/modify-playlist/<playlist_id>', methods=['POST'])
def modify_playlist(playlist_id):
    if 'access_token' not in session:
        return redirect(url_for('login'))
    
    data = request.json
    start_index = int(data.get('startIndex'))
    end_index = int(data.get('endIndex'))
    
    tracks = get_playlist_tracks(session['access_token'], playlist_id)

    if not tracks or start_index < 0 or end_index >= len(tracks):
        return "Invalid range specified.", 400

    selected_tracks = [track['track']['uri'] for track in tracks[start_index:end_index + 1]]
    
    new_playlist_id = create_new_playlist(session['access_token'], selected_tracks)
    if new_playlist_id:
        return {"message": "New playlist created successfully.", "playlist_id": new_playlist_id}, 200
    else:
        return "Failed to create new playlist.", 500

def get_playlist_tracks(access_token, playlist_id):
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(url, headers=headers)
    
    if response.ok:
        return response.json().get('items', [])
    else:
        print("Failed to fetch playlist tracks.")
        return []

def create_new_playlist(access_token, tracks):
    user_id = session['user_id']
    playlist_url = f'https://api.spotify.com/v1/users/{user_id}/playlists'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    playlist_data = {
        'name': 'Made by AbuPisac',
        'description': 'A playlist created by selecting specific tracks.',
        'public': True
    }
    
    response = requests.post(playlist_url, headers=headers, json=playlist_data)

    if response.ok:
        playlist_id = response.json()['id']
        add_tracks_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
        add_tracks_response = requests.post(add_tracks_url, headers=headers, json={'uris': tracks})
        
        if add_tracks_response.ok:
            return playlist_id
        else:
            print("Failed to add tracks to the playlist:", add_tracks_response.text)
            return None
    else:
        print("Failed to create new playlist:", response.text)
        return None

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)