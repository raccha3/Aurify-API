import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import colorsys

from flask import Flask, request, url_for, session, redirect, send_file, render_template_string
from PIL import Image, ImageDraw, ImageFilter
import io
import base64
import math

app = Flask(__name__)

app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'
app.secret_key = 'kjkdfjai*923nsfkiO^^&'
TOKEN_INFO = 'token_info'

@app.route('/')
def login():
    auth_url = create_spotify_oauth().get_authorize_url()
    return redirect(auth_url)

@app.route('/redirect')
def redirect_page():
    session.clear()
    code = request.args.get('code')
    token_info = create_spotify_oauth().get_access_token(code)
    session[TOKEN_INFO] = token_info
    return redirect(url_for('get_top_songs', external = True))

@app.route('/getTopSongs')
def get_top_songs():
    
    def calc_avg(feature_type, index, count, current_track):
        total = avg_vals[index]
        current_value = current_track.get(feature_type, 0)  # Use a default value of 0 if the feature is not found
        new_avg = (total + current_value) / count
        return new_avg

    try:
        token_info = get_token()
    except:
        print("User not logged in")
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    current_top_tracks = sp.current_user_top_tracks()['items']
    track_ids = []
    for track in current_top_tracks:
        track_ids.append(track['id'])

    avg_vals = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0] # energy, valence, danceability
    count = 0
    for id in track_ids:
        count += 1
        current_track = sp.audio_features(id)[0]
        avg_vals[0] = calc_avg("valence", 0, count, current_track)
        avg_vals[1] = calc_avg("speechiness", 1, count, current_track)
        avg_vals[2] = calc_avg("acousticness", 2, count, current_track)
        avg_vals[3] = calc_avg("danceability", 3, count, current_track)
        avg_vals[4] = calc_avg("energy", 4, count, current_track)
        avg_vals[5] = calc_avg("instrumentalness", 5, count, current_track)
    
    avg_vals = [min(val * 10, 1) for val in avg_vals]

    # Aura generation code
    # Define colors for the aura (RGB tuples)
    colors = [decimal_to_hsv_color(avg_vals[0], avg_vals[1], avg_vals[2]), 
              decimal_to_hsv_color(avg_vals[3], avg_vals[4], avg_vals[5])]  # Red, Green, Blue
    size = (1920, 1080)  # Size of the image to create

    aura_image = create_aura_image(colors, size)

    # Save the image to a bytes buffer
    buf = io.BytesIO()
    aura_image.save(buf, format='PNG')
    buf.seek(0)

    # Encode the image for embedding
    image_data = base64.b64encode(buf.getvalue()).decode('latin1')

    # Serve the image as a full-page background
    return render_template_string("""
        <!doctype html>
        <html>
        <head>
            <title>Aura Background</title>
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background-image: url('data:image/png;base64,{{image_data}}');
                    background-size: cover;
                    background-position: center center;
                    background-attachment: fixed;
                }
            </style>
        </head>
        <body>
        </body>
        </html>
        """, image_data=image_data) 


def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        redirect(url_for('login', external=False))

    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id = "2e5884db683b4b80be98238887a382c7",
        client_secret = "1f3fa91bfea24edc9db5fcd6204d6dd7",
        redirect_uri = url_for('redirect_page', _external = True),
        scope = 'user-top-read'
        )

def create_aura_image(colors, size):
    image = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(image)

    min_dimension = min(size)
    
    for i, color in enumerate(colors):
        # Convert the color from HSV to RGB
        rgb_color = colorsys.hsv_to_rgb(*color)

        # Scale RGB values to the range 0-255
        scaled_rgb_color = tuple(int(component * 255) for component in rgb_color)

        # Calculate the radius for the circle
        radius = min_dimension // 2 - i * min_dimension // (2 * len(colors))

        # Calculate bounding box for the circle
        upper_left = (size[0] // 2 - radius, size[1] // 2 - radius)
        lower_right = (size[0] // 2 + radius, size[1] // 2 + radius)
        draw.ellipse([upper_left, lower_right], fill=scaled_rgb_color)

    blurred_image = image.filter(ImageFilter.GaussianBlur(radius=max(size)//30))
    return blurred_image

def decimal_to_hsv_color(val1, val2, val3):
    hue = val1 % 1  # Use modulo to wrap hue within the range [0, 1]
    saturation = min(1 - val2, 1)  # Ensure saturation is within [0, 1]
    value = min(1 - val3, 1)  # Ensure value is within [0, 1]

    return (hue, saturation, value)

app.run(debug = True)