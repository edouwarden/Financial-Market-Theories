import requests
import ccxt
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
import matplotlib.dates as mdates  # Importing the mdates module
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from datetime import datetime
import pytz
import scrapetube
from matplotlib.widgets import CheckButtons  # Add this import
from matplotlib.widgets import Slider, TextBox, RadioButtons  # Add these imports

# Function to convert the given date-time string to Unix timestamp in milliseconds
def convert_to_unix_timestamp(date_string):
    input_format = "%Y-%m-%dT%H:%M:%S%z"
    dt = datetime.strptime(date_string, input_format)
    dt_utc = dt.astimezone(pytz.utc)
    timestamp_ms = int(dt_utc.timestamp() * 1000)
    return timestamp_ms

# Function to fetch the publication date of a YouTube video
def get_video_pubdate(video_url):
    response = requests.get(video_url)
    if response.status_code != 200:
        print(f"Failed to retrieve the video page. Status code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    meta_tag = soup.find('meta', {'itemprop': 'uploadDate'})
    if meta_tag:
        publish_date = meta_tag.get('content')
        return publish_date
    else:
        print("Publication date not found.")
        return None

# Prompt for channel username
channel_username = input("Enter YouTube channel username (without @) (default: Hasheur): ").strip()
if not channel_username:
    channel_username = 'Hasheur'

# Prompt for timeframe
valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
timeframe = input(f"Enter timeframe {valid_timeframes} (default: 8h): ").strip()
if timeframe not in valid_timeframes:
    timeframe = '8h'

# Prompt for image size
try:
    image_size = int(input("Enter maximum image size (default: 15): ").strip())
except ValueError:
    image_size = 15
if not image_size:
    image_size = 15

try:
    min_image_size = int(input("Enter minimum image size percentage (default: 10): ").strip())
except ValueError:
    min_image_size = 0.1
if not min_image_size:
    min_image_size = 0.1

dynamic_size = input("Do you want to use dynamic size for thumbnails? (yes/no, default: yes): ").strip().lower()
if dynamic_size in ['no', 'n']:
    dynamic_size = False
else:
    dynamic_size = True

print("Fetching chart data")
exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe=timeframe, limit=1000)

# Fetch YouTube videos from the channel using scrapetube
videos = scrapetube.get_channel(channel_username=channel_username)

# List to hold video details (title, pubdate, thumbnail_url)
video_details = []
max_views = 0
index = 0

print(f"Fetching videos for channel: {channel_username}")

for video in videos:
    if index >= 50:
        break
    video_id = video['videoId']
    title = video['title']
    views = int(video['viewCountText']['simpleText'].replace(' views', '').replace(',', ''))
    if views > max_views:
        max_views = views
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    published_at = get_video_pubdate(video_url)
    if published_at:
        published_at = convert_to_unix_timestamp(published_at)
        video_details.append({
            'title': title,
            'thumbnail_url': thumbnail_url,
            'published_at': published_at,
            'views': views
        })
    index += 1
    print(f"{index}/50 videos fetched")

# Fetch 4-hour BTC/USDT OHLCV data

data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
# Convert millisecond timestamps to datetime
data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')

# Plotting the BTC chart with video thumbnails below it
fig, ax1 = plt.subplots(1, 1, figsize=(14, 10), sharex=True)
plt.subplots_adjust(left=0.18, right=0.98, bottom=0.18)  # Less space for widgets, more for chart

# Plot BTC/USDT close price
ax1.plot(data['timestamp'], data['close'], label='BTC/USDT Close Price', color='blue')
ax1.set_title(f'{timeframe} BTC/USDT Chart')
ax1.set_ylabel('Price (USDT)')
ax1.grid(True)
ax1.legend()
ax1.tick_params(axis='x', rotation=45)

# Store images in memory to avoid re-downloading
for video in video_details:
    if 'img' not in video:
        img_data = requests.get(video['thumbnail_url']).content
        video['img'] = Image.open(BytesIO(img_data))

# Function to reload videos and chart when channel changes
def reload_channel(new_channel):
    global channel_username, videos, video_details, max_views, index, ohlcv, data
    channel_username = new_channel
    print(f"Fetching videos for channel: {channel_username}")
    videos = scrapetube.get_channel(channel_username=channel_username)
    video_details.clear()
    max_views = 0
    index = 0
    for video in videos:
        if index >= 50:
            break
        video_id = video['videoId']
        title = video['title']
        views = int(video['viewCountText']['simpleText'].replace(' views', '').replace(',', ''))
        if views > max_views:
            max_views = views
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        published_at = get_video_pubdate(video_url)
        if published_at:
            published_at = convert_to_unix_timestamp(published_at)
            video_details.append({
                'title': title,
                'thumbnail_url': thumbnail_url,
                'published_at': published_at,
                'views': views
            })
        index += 1
    # Store images in memory to avoid re-downloading
    for video in video_details:
        if 'img' not in video:
            img_data = requests.get(video['thumbnail_url']).content
            video['img'] = Image.open(BytesIO(img_data))
    # Re-fetch chart data for current timeframe
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe=timeframe, limit=1000)
    data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    ax1.clear()
    ax1.plot(data['timestamp'], data['close'], label='BTC/USDT Close Price', color='blue')
    ax1.set_title(f'{timeframe} BTC/USDT Chart')
    ax1.set_ylabel('Price (USDT)')
    ax1.grid(True)
    ax1.legend()
    ax1.tick_params(axis='x', rotation=45)
    draw_thumbnails(dynamic_size)

# Function to draw thumbnails
def draw_thumbnails(dynamic_size):
    # Remove previous thumbnails
    for artist in list(ax1.artists):
        artist.remove()
    for video in video_details:
        video_time = pd.to_datetime(video['published_at'], unit='ms')
        closest_idx = (data['timestamp'] - video_time).abs().argmin()
        x_pos = data['timestamp'].iloc[closest_idx]
        y_pos = data['close'].iloc[closest_idx]
        if dynamic_size:
            zoom_value = max(min_image_size, video['views'] / max_views) * (image_size / 100)
        else:
            zoom_value = image_size / 100
        imagebox = OffsetImage(video['img'], zoom=zoom_value)
        ab = AnnotationBbox(imagebox, (x_pos, y_pos), frameon=False)
        ax1.add_artist(ab)
    fig.canvas.draw_idle()

# Function to update chart and thumbnails when timeframe or image_size changes
def update_chart(new_timeframe=None, new_image_size=None):
    global data, ohlcv, image_size, timeframe, max_views
    if new_timeframe:
        timeframe = new_timeframe
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe=timeframe, limit=1000)
        data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
        ax1.clear()
        ax1.plot(data['timestamp'], data['close'], label='BTC/USDT Close Price', color='blue')
        ax1.set_title(f'{timeframe} BTC/USDT Chart')
        ax1.set_ylabel('Price (USDT)')
        ax1.grid(True)
        ax1.legend()
        ax1.tick_params(axis='x', rotation=45)
    if new_image_size is not None:
        image_size = new_image_size
    draw_thumbnails(dynamic_size)

# Initial draw
draw_thumbnails(dynamic_size)

# Add a CheckButtons widget for dynamic size toggle
ax_check = plt.axes([0.01, 0.8, 0.13, 0.08])
check = CheckButtons(ax_check, ['Dynamic Size'], [dynamic_size])

def on_toggle(label):
    global dynamic_size
    dynamic_size = not dynamic_size
    draw_thumbnails(dynamic_size)

check.on_clicked(on_toggle)

# Add a RadioButtons widget for timeframe selection
ax_timeframe = plt.axes([0.01, 0.45, 0.13, 0.33])
radio_timeframe = RadioButtons(ax_timeframe, valid_timeframes, active=valid_timeframes.index(timeframe))

def on_timeframe(label):
    update_chart(new_timeframe=label)

radio_timeframe.on_clicked(on_timeframe)

# Add a Slider for image size
ax_slider_label = plt.axes([0.01, 0.38, 0.13, 0.015], frameon=False)
ax_slider_label.set_axis_off()
ax_slider_label.text(0.5, 0.5, 'Img Size', ha='center', va='center', fontsize=10)
ax_slider = plt.axes([0.01, 0.35, 0.13, 0.03])
slider = Slider(ax_slider, '', 5, 50, valinit=image_size, valstep=1)

def on_slider(val):
    update_chart(new_image_size=int(val))
    textbox.set_val(str(int(val)))  # Sync textbox

slider.on_changed(on_slider)

# Add a TextBox for image size
ax_text = plt.axes([0.01, 0.31, 0.13, 0.03])
ax_text_label = plt.axes([0.01, 0.34, 0.13, 0.015], frameon=False)
ax_text_label.set_axis_off()
ax_text_label.text(0.5, 0.5, 'Img Size', ha='center', va='center', fontsize=10)
textbox = TextBox(ax_text, '', initial=str(image_size))

def on_text_submit(text):
    try:
        val = int(text)
        if 5 <= val <= 50:
            slider.set_val(val)
            update_chart(new_image_size=val)
    except ValueError:
        pass  # Ignore invalid input

textbox.on_submit(on_text_submit)

# Add a TextBox for minimum image size
ax_min_text = plt.axes([0.01, 0.26, 0.13, 0.03])
ax_min_text_label = plt.axes([0.01, 0.29, 0.13, 0.015], frameon=False)
ax_min_text_label.set_axis_off()
ax_min_text_label.text(0.5, 0.5, 'Min Img Size percent', ha='center', va='center', fontsize=10)
min_textbox = TextBox(ax_min_text, '', initial=str(int(min_image_size * 100)))  # Show as percentage

def on_min_text_submit(text):
    global min_image_size
    try:
        val = int(text)
        if 1 <= val <= 100:  # Assuming percentage input
            min_image_size = val/100  # Convert to percentage
            min_textbox.set_val(str(val))  # Ensure field shows clamped value
            update_chart()
        else:
            min_textbox.set_val(str(min_image_size * 100))  # Reset to last valid value

    except ValueError:
        pass

min_textbox.on_submit(on_min_text_submit)

plt.tight_layout(rect=[0.18, 0.18, 1, 1])  # Adjust layout for widgets

# Show the plot
plt.show()
