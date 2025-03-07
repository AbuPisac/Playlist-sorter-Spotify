from flask import Flask, session, redirect, url_for, render_template, request
import os
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

CLIENT_ID = 'a61630d5ce474d0cb89504a3b9db1b4b'
CLIENT_SECRET = '2719c0085bca43e9b64a98cccf19c094'
REDIRECT_URI = 'http://localhost:5000/callback'
SCOPE = 'playlist-read-private user-read-email playlist-modify-public playlist-read-collaborative playlist-modify-private user-follow-modify user-follow-read user-read-private'

@app.route('/')
def home():
    return '<a href="/login">Login with Spotify</a>'

@app.route('/login')
def login():
    auth_url = (
        'https://accounts.spotify.com/authorize'
        f'?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPE}'
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_url = 'https://accounts.spotify.com/api/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response = requests.post(token_url, headers=headers, data=data)
    access_token = response.json().get('access_token')
    session['access_token'] = access_token
    return redirect(url_for('view_playlists'))

@app.route('/playlists')
def view_playlists():
    access_token = session.get('access_token')
    if not access_token:
        return "User is not logged in", 401

    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    playlist_url = 'https://api.spotify.com/v1/me/playlists'
    response = requests.get(playlist_url, headers=headers)

    if response.ok:
        playlists = response.json().get('items', [])
        return render_template('playlists.html', playlists=playlists)
    else:
        return f"Failed to retrieve playlists: {response.status_code}", response.status_code

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
