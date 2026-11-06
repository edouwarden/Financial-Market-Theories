import requests
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
        # Initialize Tkinter root
        self.root = tk.Tk()
        self.root.title("YouTube Thumbnails Timeline")
        
        # Create matplotlib figure and axes FIRST
        print("Creating matplotlib figure and axes...")
        plt.ioff()  # Turn off interactive mode to prevent extra windows
        self.fig = plt.figure(figsize=(12, 12))
        self.ax1 = self.fig.add_subplot(111)
        
        # Initialize data attributes
        self.video_details = []
        
        # Default YouTubers to track
        self.youtubers = ['Hasheur', 'CryptoMatrix', 'CoinBureau', 'Altcoin Daily']
        
        # Create control frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Add YouTuber entry and button
        self.youtuber_var = tk.StringVar()
        ttk.Label(control_frame, text="Add YouTuber:").pack(side=tk.LEFT, padx=(0, 5))
        self.youtuber_entry = ttk.Entry(control_frame, textvariable=self.youtuber_var)
        self.youtuber_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(control_frame, text="Add", command=self.add_youtuber).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="Refresh", command=self.refresh_data).pack(side=tk.LEFT, padx=(5, 0))
        
        # Create YouTuber list frame
        list_frame = ttk.Frame(self.root)
        list_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Add YouTuber list
        ttk.Label(list_frame, text="Current YouTubers:").pack(side=tk.TOP, anchor='w')
        self.youtuber_listbox = tk.Listbox(list_frame, height=4)
        self.youtuber_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add scrollbar to listbox
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.youtuber_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.youtuber_listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate listbox
        for youtuber in self.youtubers:
            self.youtuber_listbox.insert(tk.END, youtuber)
        
        # Add remove button
        ttk.Button(list_frame, text="Remove", command=self.remove_youtuber).pack(side=tk.BOTTOM, pady=(5, 0))
        
        # Create slider frame
        slider_frame = ttk.Frame(self.root)
        slider_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Add zoom slider
        ttk.Label(slider_frame, text="Thumbnail Size:").pack(side=tk.LEFT)
        self.zoom_slider = ttk.Scale(slider_frame, from_=0.05, to=0.3, orient=tk.HORIZONTAL)
        self.zoom_slider.set(0.15)
        self.zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add limit slider for number of videos per channel
        ttk.Label(slider_frame, text="Videos per channel:").pack(side=tk.LEFT, padx=(10, 0))
        self.limit_slider = ttk.Scale(slider_frame, from_=5, to=50, orient=tk.HORIZONTAL)
        self.limit_slider.set(10)
        self.limit_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create canvas for the matplotlib figure
        print("Creating canvas for matplotlib figure...")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add loading label
        self.loading_label = ttk.Label(self.root, text="Loading data...")
        self.loading_label.pack(side=tk.TOP, pady=5)
        self.root.update()  # Force update to show loading label
        
        # Initialize data
        self.setup_data()
        
        # Remove loading label
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.destroy()
        
        # Initial plot
        self.update_plot()
        
        # Now connect the sliders to the update_plot method
        self.zoom_slider.config(command=self.update_plot)
        self.limit_slider.config(command=self.update_plot)
        
    def add_youtuber(self):
        youtuber = self.youtuber_var.get().strip()
        if youtuber and youtuber not in self.youtubers:
            self.youtubers.append(youtuber)
            self.youtuber_listbox.insert(tk.END, youtuber)
            self.youtuber_var.set('')  # Clear entry
            self.refresh_data()
    
    def remove_youtuber(self):
        selected = self.youtuber_listbox.curselection()
        if selected:
            index = selected[0]
            youtuber = self.youtuber_listbox.get(index)
            self.youtubers.remove(youtuber)
            self.youtuber_listbox.delete(index)
            self.refresh_data()
    
    def refresh_data(self):
        # Create and show loading label
        self.loading_label = ttk.Label(self.root, text="Loading data...")
        self.loading_label.pack(side=tk.TOP, pady=5)
        self.root.update()  # Force update to show loading label
        
        # Reload data
        self.setup_data()
        
        # Remove loading label
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.destroy()
            
        # Update the plot
        self.update_plot()
    
    def setup_data(self):
        try:
            # List to hold video details
            self.video_details = []
            
            # Get videos per channel limit
            videos_per_channel = int(self.limit_slider.get())
            
            # Fetch videos from each YouTuber
            for channel_username in self.youtubers:
                try:
                    videos = scrapetube.get_channel(channel_username=channel_username)
                    
                    index = 0
                    for video in videos:
                        if index >= videos_per_channel:
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
                                'video_id': video_id,
                                'channel': channel_username
                            })
                        index += 1
                except Exception as e:
                    print(f"Error fetching videos for {channel_username}: {e}")
            
            # Sort videos by publication date (newest first)
            self.video_details = sorted(self.video_details, key=lambda x: x['published_at'], reverse=True)
                
        except Exception as e:
            print(f"Error in setup_data: {e}")
            self.video_details = []
    
    def update_plot(self, *args):
        try:
            # Ensure we have a valid figure, axes, and canvas
            if not hasattr(self, 'fig') or not hasattr(self, 'ax1') or not hasattr(self, 'canvas'):
                print("Error: Figure, axes or canvas not initialized properly")
                return
                
            # Clear the current plot
            print("Clearing plot...")
            self.ax1.clear()
            
            if not self.video_details:
                print("No videos available, displaying message...")
                self.ax1.text(0.5, 0.5, 'No videos available', 
                            horizontalalignment='center',
                            verticalalignment='center',
                            transform=self.ax1.transAxes)
                self.canvas.draw()
                return
            
            # Set up timeline
            print("Setting up timeline...")
            timestamps = [video['published_at'] for video in self.video_details]
            min_time = min(timestamps)
            max_time = max(timestamps)
            
            # Create a timeline
            print(f"Creating timeline from {pd.to_datetime(min_time, unit='ms')} to {pd.to_datetime(max_time, unit='ms')}")
            timeline = pd.date_range(start=pd.to_datetime(min_time, unit='ms'), 
                                    end=pd.to_datetime(max_time, unit='ms'), 
                                    freq='D')
            
            # Add a background grid
            for r in range(num_rows):
                for c in range(num_cols):
                    if r * num_cols + c < num_videos:  # Only draw cells that will have content
                        rect = plt.Rectangle(
                            (c * cell_width + margin/2, 1 - (r+1) * cell_height + margin/2),
                            cell_width - margin, cell_height - margin,
                            fill=True, color='#f9f9f9', alpha=0.3, edgecolor='#dddddd', linewidth=1
                        )
                        self.ax1.add_patch(rect)
            
            # Add video thumbnails
            zoom = float(self.zoom_slider.get())
            
            # Calculate spacing for thumbnails
            num_videos = len(self.video_details)
            y_positions = np.linspace(0.1, 0.9, num_videos)
            
            # Add color-coded legend for channels
            channels = list(set([video['channel'] for video in self.video_details]))
            channel_colors = plt.cm.tab10(np.linspace(0, 1, len(channels)))
            channel_color_map = {channel: channel_colors[i] for i, channel in enumerate(channels)}
            
            # Plot legend
            for i, channel in enumerate(channels):
                self.ax1.plot([], [], 'o', color=channel_color_map[channel], label=channel)
            self.ax1.legend(loc='upper right')
            
            # Set up a fixed grid layout instead of timeline
            self.ax1.set_title('YouTube Videos Grid (Newest to Oldest)')
            
            # Hide axes since we're using a grid layout
            self.ax1.get_xaxis().set_visible(False)
            self.ax1.get_yaxis().set_visible(False)
            
            # Set fixed axis limits
            self.ax1.set_xlim(0, 1)
            self.ax1.set_ylim(0, 1)
            
            # Calculate grid dimensions based on number of videos
            num_cols = 4  # Number of columns in the grid
            num_rows = (num_videos + num_cols - 1) // num_cols  # Ceiling division
            
            # Calculate cell size with margins
            cell_width = 1.0 / num_cols
            cell_height = 1.0 / num_rows
            margin = 0.01  # Margin between cells
            
            # Create grid coordinates
            grid_x = np.linspace(cell_width/2, 1 - cell_width/2, num_cols)
            grid_y = np.linspace(1 - cell_height/2, cell_height/2, num_rows)  # Top to bottom
            
            # Plot thumbnails in a grid
            for i, video in enumerate(self.video_details):
                # Calculate grid position
                row = i // num_cols
                col = i % num_cols
                
                x_pos = grid_x[col]
                y_pos = grid_y[row]
                
                # Get cached image
                img = get_cached_image(video['video_id'], video['thumbnail_url'])
                imagebox = OffsetImage(img, zoom=zoom)
                
                # Add colored dot for channel
                channel_color = channel_color_map[video['channel']]
                self.ax1.plot(x_pos, y_pos, 'o', color=channel_color, markersize=10, zorder=10)  # Higher zorder to be on top
                
                # Add thumbnail
                ab = AnnotationBbox(imagebox, (x_pos, y_pos), 
                                  frameon=True, 
                                  bboxprops=dict(boxstyle="round,pad=0.3", 
                                                fc="white", 
                                                ec=channel_color, 
                                                lw=2),
                                  zorder=20)  # Higher zorder to be on top
                self.ax1.add_artist(ab)
                
                # Add video title and publication date
                try:
                    # Get title safely
                    title_text = str(video['title'])
                    if len(title_text) > 30:
                        title_text = title_text[:30] + "..."
                    
                    # Format date
                    pub_date = pd.to_datetime(video['published_at'], unit='ms').strftime('%Y-%m-%d')
                    text = f"{title_text}\n{pub_date} - {video['channel']}"
                    
                    # Add annotation
                    self.ax1.annotate(text, 
                                    xy=(x_pos, y_pos), 
                                    xytext=(0, -30), 
                                    textcoords="offset points", 
                                    fontsize=8, 
                                    ha='center', 
                                    va='top',
                                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                                    zorder=30)
                except Exception as e:
                    print(f"Error annotating video {i}: {e}")
            
            print("Applying tight_layout and drawing canvas...")
            self.fig.tight_layout()
            self.canvas.draw()
            print("Plot update complete.")
        except Exception as e:
            print(f"Error in update_plot: {e}")
            if hasattr(self, 'ax1') and hasattr(self, 'canvas'):
                self.ax1.text(0.5, 0.5, f'Error updating plot: {str(e)}', 
                            horizontalalignment='center',
                            verticalalignment='center',
                            transform=self.ax1.transAxes)
                self.canvas.draw()
    
    def run(self):
        try:
            # Center the window
            window_width = 1200
            window_height = 800
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            center_x = int(screen_width/2 - window_width/2)
            center_y = int(screen_height/2 - window_height/2)
            self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
            
            # Start the main loop
            self.root.mainloop()
        except Exception as e:
            print(f"Error in main loop: {e}")
            self.root.destroy()

if __name__ == "__main__":
    print("Starting YouTube Thumbnails Timeline application...")
    plt.close('all')  # Close any existing matplotlib windows
    app = ChartApp()
    print("Initialization complete, running application...")
    app.run()
