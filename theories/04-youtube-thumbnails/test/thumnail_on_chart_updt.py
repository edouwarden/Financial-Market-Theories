import requests
import ccxt
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
import matplotlib.dates as mdates
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from datetime import datetime
import pytz
import scrapetube
import os
import tkinter as tk
from tkinter import ttk
from colorthief import ColorThief
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sklearn.cluster import KMeans

# Create cache directory if it doesn't exist
CACHE_DIR = "youtube_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_dominant_color(image):
    # Convert image to numpy array
    img_array = np.array(image)
    
    # Reshape the array to 2D array of pixels
    pixels = img_array.reshape(-1, 3)
    
    # Convert to float32 for better precision
    pixels = pixels.astype(np.float32)
    
    # Use K-means clustering to find dominant colors
    kmeans = KMeans(n_clusters=1, random_state=42)
    kmeans.fit(pixels)
    
    # Get the dominant color (cluster center)
    dominant_color = kmeans.cluster_centers_[0].astype(np.uint8)
    
    # Convert to tuple for PIL
    return tuple(dominant_color)

def get_cached_image(video_id, thumbnail_url):
    cache_path = os.path.join(CACHE_DIR, f"{video_id}.png")
    
    if os.path.exists(cache_path):
        return Image.open(cache_path)
    
    # Download and process image if not in cache
    img_data = requests.get(thumbnail_url).content
    img = Image.open(BytesIO(img_data))
    
    # Get dominant color from original image
    dominant_color = get_dominant_color(img)
    
    # Add border with dominant color
    border_width = 300  # Increased border width
    new_size = (img.width + 2*border_width, img.height + 2*border_width)
    
    # Create a new image with the dominant color
    bordered_img = Image.new('RGB', new_size, dominant_color)
    
    # Create a gradient effect for the border
    for i in range(border_width):
        # Calculate alpha for gradient effect
        alpha = 1 - (i / border_width)
        # Create a slightly darker version of the dominant color for the gradient
        gradient_color = tuple(int(c * (0.8 + 0.2 * alpha)) for c in dominant_color)
        # Draw the gradient border
        bordered_img.paste(gradient_color, (i, i, new_size[0]-i, new_size[1]-i))
    
    # Paste the original image in the center
    bordered_img.paste(img, (border_width-10, border_width-10))
    
    # Save to cache
    bordered_img.save(cache_path)
    return bordered_img

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

class ChartApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BTC Chart with YouTube Thumbnails")
        
        # Initialize data attributes
        self.data = pd.DataFrame()
        self.video_details = []
        
        # Create matplotlib figure first
        self.fig, self.ax1 = plt.subplots(1, 1, figsize=(12, 12))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Create slider frame
        slider_frame = ttk.Frame(self.root)
        slider_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Add zoom slider
        ttk.Label(slider_frame, text="Thumbnail Size:").pack(side=tk.LEFT)
        self.zoom_slider = ttk.Scale(slider_frame, from_=0.05, to=0.3, orient=tk.HORIZONTAL, 
                                   command=self.update_plot)
        self.zoom_slider.set(0.15)
        self.zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add loading label
        self.loading_label = ttk.Label(self.root, text="Loading data...")
        self.loading_label.pack(side=tk.TOP, pady=5)
        
        # Initialize data
        self.setup_data()
        
        # Remove loading label
        self.loading_label.destroy()
        
        # Initial plot
        self.update_plot()
        
    def setup_data(self):
        try:
            # Fetch YouTube videos
            channel_username = 'Hasheur'
            videos = scrapetube.get_channel(channel_username=channel_username)
            
            # List to hold video details
            self.video_details = []
            index = 0
            
            for video in videos:
                if index >= 50:
                    break
                video_id = video['videoId']
                title = video['title']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                published_at = get_video_pubdate(video_url)
                if published_at:
                    published_at = convert_to_unix_timestamp(published_at)
                    self.video_details.append({
                        'title': title,
                        'thumbnail_url': thumbnail_url,
                        'published_at': published_at,
                        'video_id': video_id
                    })
                index += 1
            
            # Fetch BTC data
            exchange = ccxt.binance()
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='8h', limit=800)
            self.data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.data['timestamp'] = pd.to_datetime(self.data['timestamp'], unit='ms')
            
            if self.data.empty:
                raise Exception("No BTC data was fetched")
                
        except Exception as e:
            print(f"Error in setup_data: {e}")
            self.video_details = []
            self.data = pd.DataFrame()
            raise  # Re-raise the exception to handle it in __init__
    
    def update_plot(self, *args):
        try:
            # Clear the current plot
            self.ax1.clear()
            
            if self.data.empty:
                self.ax1.text(0.5, 0.5, 'No data available', 
                            horizontalalignment='center',
                            verticalalignment='center',
                            transform=self.ax1.transAxes)
                self.canvas.draw()
                return
            
            # Plot BTC/USDT close price
            self.ax1.plot(self.data['timestamp'], self.data['close'], 
                         label='BTC/USDT Close Price', color='blue')
            self.ax1.set_title('4-Hour BTC/USDT Chart')
            self.ax1.set_ylabel('Price (USDT)')
            self.ax1.grid(True)
            self.ax1.legend()
            self.ax1.tick_params(axis='x', rotation=45)
            
            # Add video thumbnails
            zoom = float(self.zoom_slider.get())
            
            for video in self.video_details:
                video_time = pd.to_datetime(video['published_at'], unit='ms')
                closest_idx = (self.data['timestamp'] - video_time).abs().argmin()
                x_pos = self.data['timestamp'].iloc[closest_idx]
                y_pos = self.data['close'].iloc[closest_idx]
                
                # Get cached image
                img = get_cached_image(video['video_id'], video['thumbnail_url'])
                imagebox = OffsetImage(img, zoom=zoom)
                ab = AnnotationBbox(imagebox, (x_pos, y_pos), frameon=False)
                self.ax1.add_artist(ab)
            
            self.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            print(f"Error in update_plot: {e}")
            self.ax1.text(0.5, 0.5, f'Error updating plot: {str(e)}', 
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=self.ax1.transAxes)
            self.canvas.draw()
    
    def run(self):
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"Error in main loop: {e}")
            self.root.destroy()

if __name__ == "__main__":
    app = ChartApp()
    app.run()
