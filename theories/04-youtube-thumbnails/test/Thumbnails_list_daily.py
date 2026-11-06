import requests
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageTk
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import scrapetube
import os
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import numpy as np
from sklearn.cluster import KMeans
import time
import threading
import queue
import json
import re
from pathlib import Path

# Create cache directories if they don't exist
CACHE_DIR = "youtube_cache"
COMPOSITE_DIR = "composite_images"
METADATA_DIR = "youtube_metadata"
FETCH_CACHE_DIR = "fetch_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
if not os.path.exists(COMPOSITE_DIR):
    os.makedirs(COMPOSITE_DIR)
if not os.path.exists(METADATA_DIR):
    os.makedirs(METADATA_DIR)
if not os.path.exists(FETCH_CACHE_DIR):
    os.makedirs(FETCH_CACHE_DIR)
    
# Rate limiting constants
REQUEST_DELAY = 1.0  # Seconds between requests to YouTube
MAX_CONCURRENT_REQUESTS = 2  # Maximum number of concurrent requests

def get_cached_image(video_id, thumbnail_url):
    cache_path = os.path.join(CACHE_DIR, f"{video_id}.png")
    
    if os.path.exists(cache_path):
        # Open cached image
        img = Image.open(cache_path)
        # Process the cached image to remove black borders if present
        img = remove_black_borders(img)
        return img
    
    # Download and process image if not in cache
    img_data = requests.get(thumbnail_url).content
    img = Image.open(BytesIO(img_data))
    
    # Remove black borders from the downloaded image
    img = remove_black_borders(img)
    
    # Save the processed image to cache
    img.save(cache_path)
    return img

def remove_black_borders(img):
    """Remove black borders from an image by cropping them out"""
    # Convert image to numpy array
    img_array = np.array(img)
    
    # Check if the image has black borders at the top and bottom
    # A black border is defined as rows where most pixels are very dark
    height, width = img_array.shape[:2]
    
    # Define threshold for "black" - not pure black to account for compression artifacts
    black_threshold = 20
    
    # Find the first non-black row from the top
    top_crop = 0
    for i in range(height):
        row = img_array[i]
        # Check if the row is mostly black (average brightness below threshold)
        if np.mean(row) > black_threshold:
            top_crop = i
            break
    
    # Find the first non-black row from the bottom
    bottom_crop = height - 1
    for i in range(height - 1, -1, -1):
        row = img_array[i]
        if np.mean(row) > black_threshold:
            bottom_crop = i
            break
    
    # Only crop if we found black borders
    if top_crop > 0 or bottom_crop < height - 1:
        # Ensure we don't crop too much (sanity check)
        if bottom_crop - top_crop > height * 0.5:  # Ensure we keep at least 50% of the image
            return img.crop((0, top_crop, width, bottom_crop + 1))
    
    # Return the original image if no borders were found or if cropping would be too aggressive
    return img

def get_dominant_color(image, k=5):
    """Get the dominant color from an image using K-means clustering"""
    try:
        # Resize image to speed up processing
        image = image.resize((150, 150))
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Reshape to list of pixels
        pixels = img_array.reshape(-1, 3)
        
        # Use K-means to find dominant colors
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # Get the most common cluster (dominant color)
        labels = kmeans.labels_
        unique, counts = np.unique(labels, return_counts=True)
        dominant_cluster = unique[np.argmax(counts)]
        dominant_color = kmeans.cluster_centers_[dominant_cluster]
        
        # Convert to RGB tuple
        return tuple(int(c) for c in dominant_color)
    except Exception as e:
        print(f"Error getting dominant color: {e}")
        return (128, 128, 128)  # Default gray

def get_green_red_ratio(image):
    """Analyze if an image is more green or red dominant using improved color analysis"""
    try:
        # Resize image to speed up processing
        image = image.resize((150, 150))
        
        # Convert to numpy array for RGB analysis
        rgb_array = np.array(image)
        
        # Method 1: RGB channel dominance analysis
        # Calculate how much each channel dominates
        r_channel = rgb_array[:, :, 0].astype(np.float32)
        g_channel = rgb_array[:, :, 1].astype(np.float32)
        b_channel = rgb_array[:, :, 2].astype(np.float32)
        
        # Calculate average values
        avg_r = np.mean(r_channel)
        avg_g = np.mean(g_channel)
        avg_b = np.mean(b_channel)
        
        # Method 2: HSV analysis for more accurate color detection
        hsv_image = image.convert('HSV')
        hsv_array = np.array(hsv_image)
        hue = hsv_array[:, :, 0]
        saturation = hsv_array[:, :, 1]
        value = hsv_array[:, :, 2]
        
        # More inclusive green and red ranges
        # Green: 35-165 degrees (broader range)
        # Red: 0-25 and 335-360 degrees (broader range)
        green_mask = ((hue >= 35) & (hue <= 165)) & (saturation > 20) & (value > 20)
        red_mask = (((hue >= 0) & (hue <= 25)) | ((hue >= 335) & (hue <= 360))) & (saturation > 20) & (value > 20)
        
        green_pixels = np.sum(green_mask)
        red_pixels = np.sum(red_mask)
        
        # Method 3: Improved weighted color analysis
        # Count pixels that are clearly green or red dominant
        green_dominant_pixels = 0
        red_dominant_pixels = 0
        
        for i in range(rgb_array.shape[0]):
            for j in range(rgb_array.shape[1]):
                r, g, b = rgb_array[i, j]
                
                # More balanced color dominance detection
                if g > r + 20 and g > b + 15:  # Clearly green dominant
                    green_dominant_pixels += 1
                elif r > g + 20 and r > b + 15:  # Clearly red dominant
                    red_dominant_pixels += 1
        
        # Combine all methods for final decision with better weighting
        # RGB channel analysis (normalized)
        rgb_green_score = max(0, (avg_g - avg_r) / 255.0) + max(0, (avg_g - avg_b) / 255.0)
        rgb_red_score = max(0, (avg_r - avg_g) / 255.0) + max(0, (avg_r - avg_b) / 255.0)
        
        # HSV pixel count (normalized by total pixels)
        total_pixels = rgb_array.shape[0] * rgb_array.shape[1]
        hsv_green_score = green_pixels / total_pixels
        hsv_red_score = red_pixels / total_pixels
        
        # Dominant pixel count (normalized)
        dominant_green_score = green_dominant_pixels / total_pixels
        dominant_red_score = red_dominant_pixels / total_pixels
        
        # Weighted combination with more balanced weights
        total_green_score = rgb_green_score * 0.4 + hsv_green_score * 0.4 + dominant_green_score * 0.2
        total_red_score = rgb_red_score * 0.4 + hsv_red_score * 0.4 + dominant_red_score * 0.2
        
        # Debug output for problematic images
        if total_green_score > 0 or total_red_score > 0:
            print(f"  RGB: G={avg_g:.1f}, R={avg_r:.1f}, B={avg_b:.1f}")
            print(f"  HSV: Green pixels={green_pixels}, Red pixels={red_pixels}")
            print(f"  Dominant: Green={green_dominant_pixels}, Red={red_dominant_pixels}")
            print(f"  Normalized: Green={total_green_score:.3f}, Red={total_red_score:.3f}")
        
        # Make decision with more lenient thresholds
        if total_green_score > total_red_score * 1.1:  # Green needs to be only 10% more
            return 'green'
        elif total_red_score > total_green_score * 1.1:  # Red needs to be only 10% more
            return 'red'
        else:
            return 'neutral'
                
    except Exception as e:
        print(f"Error analyzing green/red ratio: {e}")
        return 'neutral'

# Function to convert the given date-time string to Unix timestamp in milliseconds
def convert_to_unix_timestamp(date_string):
    input_format = "%Y-%m-%dT%H:%M:%S%z"
    dt = datetime.strptime(date_string, input_format)
    dt_utc = dt.astimezone(pytz.utc)
    timestamp_ms = int(dt_utc.timestamp() * 1000)
    return timestamp_ms

# Function to fetch the publication date of a YouTube video with caching
def get_video_pubdate(video_id, video_url):
    # Check if we have cached metadata
    metadata_path = os.path.join(METADATA_DIR, f"{video_id}.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                if 'publish_date' in metadata:
                    return metadata['publish_date']
        except Exception as e:
            print(f"Error reading cached metadata: {e}")
    
    # Delay to respect rate limits
    time.sleep(REQUEST_DELAY)
    
    # Fetch from YouTube
    try:
        response = requests.get(video_url, timeout=10)
        if response.status_code != 200:
            print(f"Failed to retrieve the video page. Status code: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        meta_tag = soup.find('meta', {'itemprop': 'uploadDate'})
        if meta_tag:
            publish_date = meta_tag.get('content')
            
            # Cache the result
            try:
                with open(metadata_path, 'w') as f:
                    json.dump({'publish_date': publish_date}, f)
            except Exception as e:
                print(f"Error caching metadata: {e}")
                
            return publish_date
        else:
            print(f"Publication date not found for {video_id}.")
            return None
    except Exception as e:
        print(f"Error fetching video data: {e}")
        return None

# Function to fetch view count for a YouTube video with caching
def get_video_view_count(video_id, video_url):
    # Check if we have cached metadata
    metadata_path = os.path.join(METADATA_DIR, f"{video_id}.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                if 'view_count' in metadata:
                    return metadata['view_count']
        except Exception as e:
            print(f"Error reading cached metadata: {e}")
    
    # Delay to respect rate limits
    time.sleep(REQUEST_DELAY)
    
    # Fetch from YouTube
    try:
        response = requests.get(video_url, timeout=10)
        if response.status_code != 200:
            print(f"Failed to retrieve the video page. Status code: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try multiple selectors for view count
        view_count = None
        
        # Method 1: Look for view count in meta tags
        meta_tag = soup.find('meta', {'itemprop': 'interactionCount'})
        if meta_tag:
            try:
                view_count = int(meta_tag.get('content', '0'))
            except ValueError:
                pass
        
        # Method 2: Look for view count in script tags
        if not view_count:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'viewCount' in script.string:
                    try:
                        # Extract view count using regex
                        import re
                        match = re.search(r'"viewCount":"?(\d+)"?', script.string)
                        if match:
                            view_count = int(match.group(1))
                            break
                    except (ValueError, AttributeError):
                        continue
        
        # Method 3: Look for view count in page text
        if not view_count:
            page_text = soup.get_text()
            import re
            # Look for patterns like "1.2M views" or "1,234,567 views"
            view_patterns = [
                r'(\d+(?:,\d+)*)\s*views?',
                r'(\d+\.?\d*[KMB])\s*views?'
            ]
            for pattern in view_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    try:
                        view_str = match.group(1)
                        if 'K' in view_str.upper():
                            view_count = int(float(view_str.replace('K', '').replace('k', '')) * 1000)
                        elif 'M' in view_str.upper():
                            view_count = int(float(view_str.replace('M', '').replace('m', '')) * 1000000)
                        elif 'B' in view_str.upper():
                            view_count = int(float(view_str.replace('B', '').replace('b', '')) * 1000000000)
                        else:
                            view_count = int(view_str.replace(',', ''))
                        break
                    except ValueError:
                        continue
        
        if view_count is not None:
            # Cache the result
            try:
                # Load existing metadata if available
                existing_metadata = {}
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        existing_metadata = json.load(f)
                
                # Update with view count
                existing_metadata['view_count'] = view_count
                
                with open(metadata_path, 'w') as f:
                    json.dump(existing_metadata, f)
            except Exception as e:
                print(f"Error caching view count: {e}")
                
            return view_count
        else:
            print(f"View count not found for {video_id}.")
            return None
    except Exception as e:
        print(f"Error fetching video view count: {e}")
        return None

# Functions to manage fetch cache for YouTubers
def load_fetch_cache():
    """Load the fetch cache from disk"""
    cache_file = os.path.join(FETCH_CACHE_DIR, "fetch_cache.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading fetch cache: {e}")
            return {}
    return {}

def save_fetch_cache(cache):
    """Save the fetch cache to disk"""
    cache_file = os.path.join(FETCH_CACHE_DIR, "fetch_cache.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Error saving fetch cache: {e}")

def should_fetch_youtuber(youtuber_name, force_fetch=False):
    """Check if a YouTuber should be fetched based on cache"""
    if force_fetch:
        return True

    cache = load_fetch_cache()
    today = datetime.now().date().isoformat()

    if youtuber_name in cache:
        last_fetch = cache[youtuber_name].get('last_fetch_date')
        if last_fetch == today:
            return False  # Already fetched today

    return True  # Should fetch

def update_fetch_cache(youtuber_name):
    """Update the fetch cache for a YouTuber"""
    cache = load_fetch_cache()
    today = datetime.now().date().isoformat()

    cache[youtuber_name] = {
        'last_fetch_date': today,
        'last_fetch_timestamp': datetime.now().isoformat()
    }

    save_fetch_cache(cache)

# Functions to save/load YouTuber list
def save_youtuber_list(youtuber_list):
    """Save the YouTuber list to a file"""
    try:
        with open("youtuber_list.txt", 'w', encoding='utf-8') as f:
            for youtuber in youtuber_list:
                f.write(youtuber.strip() + '\n')
        return True
    except Exception as e:
        print(f"Error saving YouTuber list: {e}")
        return False

def load_youtuber_list():
    """Load the YouTuber list from a file"""
    try:
        if os.path.exists("youtuber_list.txt"):
            with open("youtuber_list.txt", 'r', encoding='utf-8') as f:
                youtubers = [line.strip() for line in f.readlines() if line.strip()]
            return youtubers
        return []
    except Exception as e:
        print(f"Error loading YouTuber list: {e}")
        return []

class DailyThumbnailApp:
    def __init__(self):
        # Initialize Tkinter root
        self.root = tk.Tk()
        self.root.title("YouTube Thumbnails by Day")
        
        # Initialize data attributes
        self.video_details = []
        self.current_composite_path = None
        
        # Load YouTubers from file or use default list
        saved_youtubers = load_youtuber_list()
        if saved_youtubers:
            self.youtubers = saved_youtubers
        else:
            # Default YouTubers to track (first time setup)
            self.youtubers = [
    "CoinBureau",       # ± 2,48 M abonnés :contentReference[oaicite:0]{index=0}
    "AltcoinDaily",     # ± 1,47 M :contentReference[oaicite:1]{index=1}
    "TheBitBoyX",     # ± 1,4 M :contentReference[oaicite:2]{index=2}
    "CryptosRUs",        # ± 753 K :contentReference[oaicite:3]{index=3}
    "99Bitcoins",        # ± 706 K :contentReference[oaicite:4]{index=4}
    "EllioTradesCrypto",# ± 636 K :contentReference[oaicite:5]{index=5}
    "VoskCoin",          # ± 633 K :contentReference[oaicite:6]{index=6}
    "TheMoon",          # ± 607 K :contentReference[oaicite:7]{index=7}
    "TheCryptoLark",   # ± 545 K :contentReference[oaicite:8]{index=8}
    "davincij15",
    "IvanonTech",      # ± 527 K :contentReference[oaicite:10]{index=10}
    "DataDash",          # ± 509 K :contentReference[oaicite:11]{index=11}
    "Boxmining",         # ± 471 K :contentReference[oaicite:12]{index=12}
    "MMCrypto",          # ± 386 K :contentReference[oaicite:13]{index=13}
    "AlessioRastani",   # ± 384 K :contentReference[oaicite:14]{index=14}
    "aantonop",         # ± 333 K :contentReference[oaicite:15]{index=15}
    "ChicoCrypto",      # ± 321 K :contentReference[oaicite:16]{index=16}
    "BTCSessions",      # ± 292 K :contentReference[oaicite:17]{index=17}
    "CryptoZombie",     # ± 263 K :contentReference[oaicite:18]{index=18}
    "CryptoLove",       # ± 239 K :contentReference[oaicite:19]{index=19}
    "TheModernInvestor",# ± 238 K :contentReference[oaicite:20]{index=20}
    "CryptoTips",       # ± 215 K :contentReference[oaicite:21]{index=21}
    "chrisdunntv",        # ± 210 K :contentReference[oaicite:22]{index=22}
    "Hashoshi",          # ± 190 K :contentReference[oaicite:23]{index=23}
    "CryptoDaily",      # ± 188 K :contentReference[oaicite:24]{index=24}
    "CryptoKirbyTrading",# ± 152 K :contentReference[oaicite:25]{index=25}
    "RichardHeart",     # ± 151 K :contentReference[oaicite:26]{index=26}
    "CryptoCrow",       # ± 147 K :contentReference[oaicite:27]{index=27}
    "CryptoJoker",      # ± 137 K :contentReference[oaicite:28]{index=28}
    "CryptoRevolutionChannel",  # ± 133 K :contentReference[oaicite:29]{index=29}
    "CryptoRevolutiontv",  # ± 133 K :contentReference[oaicite:29]{index=29}
    "ToneVays",         # ± 123 K :contentReference[oaicite:31]{index=31}
    "CryptoBobby",      # ± 119 K :contentReference[oaicite:32]{index=32}
    "Crypt0",            # ± 119 K :contentReference[oaicite:33]{index=33}
    "LouisThomas",      # ± 96,8 K :contentReference[oaicite:34]{index=34}
    "NuggetsNews",      # ± 95,8 K :contentReference[oaicite:35]{index=35}
    "ReadySet",  # ± 92,4 K :contentReference[oaicite:36]{index=36}
    "CobbXRP",         # ± 84,6 K :contentReference[oaicite:37]{index=37}
    "Philakone",         # ± 82,1 K :contentReference[oaicite:38]{index=38}
    "CryptoOracle",     # ± 75,5 K :contentReference[oaicite:39]{index=39}
    "DappUniversity",   # ± 68,3 K :contentReference[oaicite:40]{index=40}
    "HackCrypto",       # ± 56,2 K :contentReference[oaicite:41]{index=41}
    "Moocharoo",         # ± 51,2 K :contentReference[oaicite:42]{index=42}
    "Cryptonews",       # ± 49,2 K :contentReference[oaicite:43]{index=43}
    "NodeInvestor",     # ± 48,4 K :contentReference[oaicite:44]{index=44}
    "ScottMelker",      # ± 48 K :contentReference[oaicite:45]{index=45}
    "KeithWareing",     # ± 46,8 K :contentReference[oaicite:46]{index=46}
    "ThatMartiniGuy",  # ± 45,8 K :contentReference[oaicite:47]{index=47}
    "UndergroundTradingFr",      # ± 38,9 K :contentReference[oaicite:48]{index=48}
    "MrKristof",        # ± 38,4 K :contentReference[oaicite:49]{index=49}
    "Coffeezilla",       # ± 4,13 M :contentReference[oaicite:50]{index=50}
    "CryptoDecoded",     # ± 4,2 M :contentReference[oaicite:51]{index=51}
    "AltcoinAnalytics",  # ± 3,2 M :contentReference[oaicite:54]{index=54}
    "DeFiDaily1",         # ± 2,7 M :contentReference[oaicite:57]{index=57}
    "cherrytgbot",         # ± 2,7 M :contentReference[oaicite:57]{index=57}
    "CryptoVisionary",   # ± 2,5 M :contentReference[oaicite:58]{index=58}
    "MetaverseExplorer", # ± 2,4 M :contentReference[oaicite:59]{index=59}
    "TokenTalks",        # ± 2,3 M :contentReference[oaicite:60]{index=60}
    "TheCryptoLab",      # ± 2,0 M :contentReference[oaicite:62]{index=62}
    "BlockchainBuilder", # ± 1,9 M :contentReference[oaicite:63]{index=63}
    "CryptoInsiderOfficial",    # ± 1,7 M :contentReference[oaicite:65]{index=65}
    "YieldMaster",       # ± 1,6 M :contentReference[oaicite:66]{index=66}
    "BlockchainBasics",  # ± 1,5 M :contentReference[oaicite:67]{index=67}
    "CryptoDataHub",     # ± 1,4 M :contentReference[oaicite:68]{index=68}
    "CryptoPhilanthropist",# ± 1,3 M :contentReference[oaicite:69]{index=69}
    "MarketPulseCrypto", # ± 1,2 M :contentReference[oaicite:70]{index=70}
    "intothecryptoverse",    # ± 870 K :contentReference[oaicite:71]{index=71}
    "CryptoBanterGroup",     # ± 750 K :contentReference[oaicite:72]{index=72}
    "CryptoCasey",      # ± 950 K (ou ~420-580 K selon sources) :contentReference[oaicite:73]{index=73}
    "DiscoverCrypto_",   # ± 1,4 M :contentReference[oaicite:74]{index=74}
    "kevinoleary",     # ± 1 M :contentReference[oaicite:75]{index=75}
    "Coffeezilla",       # déjà mentionné mais très significatif
    "Hasheur",           # YouTuber français, ~682 K abonnés :contentReference[oaicite:76]{index=76}
	"insydercrypto",
	"CryptoFutur",
	"BitcoinMagazine",
	"lesroisdubitcoin",
	"CryptoLeTrone",
	"grandanglebitcoin",
	"JulienRoman",
	"Cryptolyze",
	"MonsieurTK"]
        # Create control frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Add YouTuber entry and button
        self.youtuber_var = tk.StringVar()
        ttk.Label(control_frame, text="Add YouTuber:").pack(side=tk.LEFT, padx=(0, 5))
        self.youtuber_entry = ttk.Entry(control_frame, textvariable=self.youtuber_var)
        self.youtuber_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(control_frame, text="Add", command=self.add_youtuber).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="Generate Image", command=self.refresh_data).pack(side=tk.LEFT, padx=(5, 0))
        
        # Create YouTuber list frame
        list_frame = ttk.Frame(self.root)
        list_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Add YouTuber list
        ttk.Label(list_frame, text="Current YouTubers:").pack(side=tk.TOP, anchor='w')
        self.youtuber_text = ScrolledText(list_frame, height=10, width=40)
        self.youtuber_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Populate ScrolledText
        youtuber_text = '\n'.join(self.youtubers)
        self.youtuber_text.insert('1.0', youtuber_text)
        
        # Add remove button
        ttk.Button(list_frame, text="Remove", command=self.remove_youtuber).pack(side=tk.BOTTOM, pady=(5, 0))
        
        # Create settings frame
        settings_frame = ttk.Frame(self.root)
        settings_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Add input field for number of videos per channel
        ttk.Label(settings_frame, text="Videos per channel:").pack(side=tk.LEFT, padx=(0, 5))
        self.limit_var = tk.StringVar(value="10")
        limit_entry = ttk.Entry(settings_frame, textvariable=self.limit_var, width=5)
        limit_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Add days to display input field
        ttk.Label(settings_frame, text="Days to display:").pack(side=tk.LEFT, padx=(10, 5))
        self.days_var = tk.StringVar(value="7")
        days_entry = ttk.Entry(settings_frame, textvariable=self.days_var, width=5)
        days_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Add sizing options frame
        sizing_frame = ttk.Frame(self.root)
        sizing_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(sizing_frame, text="Sizing Options:").pack(side=tk.LEFT, padx=(0, 10))
        
        # Sizing option variable
        self.sizing_option = tk.StringVar(value="5")  # Default to option 5

        # Create radio buttons for sizing options
        sizing_options = [
            ("1. Column width by total views per day", "1"),
            ("2. Column width by avg views per day", "2"),
            ("3. Thumbnail size by views (same day)", "3"),
            ("4. Thumbnail size by views (all days)", "4"),
            ("5. Default (fixed size)", "5")
        ]

        for text, value in sizing_options:
            ttk.Radiobutton(sizing_frame, text=text, variable=self.sizing_option,
                           value=value).pack(side=tk.LEFT, padx=(0, 15))

        # Create a new frame for the checkbuttons
        checkbuttons_frame = ttk.Frame(self.root)
        checkbuttons_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0, 5))

        # Add checkbutton to reverse day order
        self.reverse_days_order = tk.BooleanVar(value=False)
        ttk.Checkbutton(checkbuttons_frame, text="Reverse day order (oldest to newest)",
                       variable=self.reverse_days_order).pack(side=tk.LEFT, padx=(0, 20))

        # Add checkbutton to draw vertical lines between columns
        self.draw_vertical_lines = tk.BooleanVar(value=False)
        ttk.Checkbutton(checkbuttons_frame, text="Draw vertical lines between columns",
                       variable=self.draw_vertical_lines).pack(side=tk.LEFT, padx=(0, 20))

        # Add checkbutton for force fetch
        self.force_fetch = tk.BooleanVar(value=False)
        ttk.Checkbutton(checkbuttons_frame, text="Force fetch (ignore cache)",
                       variable=self.force_fetch).pack(side=tk.LEFT, padx=(0, 0))
        
        # Create color options frame
        color_frame = ttk.LabelFrame(self.root, text="Day Title Background Color")
        color_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0, 5))
        
        # Color option variable
        self.color_option = tk.StringVar(value="default")
        
        # Color options
        color_options = [
            ("Default (white)", "default"),
            ("Dominant color from thumbnails", "dominant"),
            ("Green/Red based on thumbnail colors", "green_red")
        ]
        
        for text, value in color_options:
            ttk.Radiobutton(color_frame, text=text, variable=self.color_option,
                           value=value).pack(side=tk.LEFT, padx=(0, 15))
        
        # Create image display frame
        self.image_frame = ttk.Frame(self.root)
        self.image_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas for image display
        self.canvas = tk.Canvas(self.image_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbars for the canvas
        self.vscrollbar = ttk.Scrollbar(self.image_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.hscrollbar = ttk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Configure canvas
        self.canvas.configure(yscrollcommand=self.vscrollbar.set, xscrollcommand=self.hscrollbar.set)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Check for existing composite image
        self.load_latest_composite()
        
        # If no existing composite found, generate a new one
        if not self.current_composite_path:
            self.refresh_data()
    
    def on_canvas_configure(self, event):
        if hasattr(self, 'image_on_canvas'):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # If we have a current image, resize it to fit the new canvas width
            if hasattr(self, 'current_composite_path') and self.current_composite_path:
                self.display_image(self.current_composite_path)
    
    def load_latest_composite(self):
        try:
            # Find the latest composite image
            composite_files = [os.path.join(COMPOSITE_DIR, f) for f in os.listdir(COMPOSITE_DIR) 
                             if f.startswith('daily_') and f.endswith('.png')]
            
            if composite_files:
                # Sort by modification time (newest first)
                latest_file = max(composite_files, key=os.path.getmtime)
                self.current_composite_path = latest_file
                self.display_image(latest_file)
                self.status_var.set(f"Loaded existing composite image: {os.path.basename(latest_file)}")
                return True
            else:
                self.status_var.set("No existing composite images found. Will generate a new one.")
                return False
        except Exception as e:
            print(f"Error loading latest composite: {e}")
            self.status_var.set(f"Error loading latest composite: {e}")
            return False
    
    def display_image(self, image_path):
        try:
            # Load the image
            img = Image.open(image_path)
            
            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            
            # If canvas has a valid width, resize image to fit
            if canvas_width > 50:  # Ensure canvas has been properly initialized
                # Calculate new height to maintain aspect ratio
                img_ratio = img.height / img.width
                new_width = canvas_width
                new_height = int(new_width * img_ratio)
                
                # Resize the image to fit canvas width
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage
            self.photo_image = ImageTk.PhotoImage(img)
            
            # Clear previous image
            self.canvas.delete("all")
            
            # Display new image
            self.image_on_canvas = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
            
            # Update scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            return True
        except Exception as e:
            print(f"Error displaying image: {e}")
            self.status_var.set(f"Error displaying image: {e}")
            return False
    
    def sync_youtuber_list(self):
        """Sync the internal youtuber list with the text widget content"""
        current_text = self.youtuber_text.get('1.0', tk.END).strip()
        if current_text:
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            self.youtubers = lines
        else:
            self.youtubers = []

    def add_youtuber(self):
        youtuber = self.youtuber_var.get().strip()
        if youtuber and youtuber not in self.youtubers:
            self.youtubers.append(youtuber)
            # Update the text widget
            current_text = self.youtuber_text.get('1.0', tk.END).strip()
            if current_text:
                self.youtuber_text.insert(tk.END, '\n' + youtuber)
            else:
                self.youtuber_text.insert('1.0', youtuber)
            # Save to file
            save_youtuber_list(self.youtubers)
            self.youtuber_var.set('')  # Clear entry
            self.status_var.set(f"Added YouTuber: {youtuber}")
    
    def remove_youtuber(self):
        try:
            # Get current text content
            current_text = self.youtuber_text.get('1.0', tk.END).strip()
            if not current_text:
                self.status_var.set("No YouTubers to remove")
                return

            # Split into lines and get current youtuber list
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]

            if not lines:
                self.status_var.set("No YouTubers to remove")
                return

            # Get the current cursor position or selection
            try:
                # Try to get selected text
                selected_text = self.youtuber_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                if selected_text:
                    youtuber_to_remove = selected_text
                else:
                    # If no selection, use the line where cursor is
                    cursor_pos = self.youtuber_text.index(tk.INSERT)
                    line_num = int(cursor_pos.split('.')[0])
                    if 1 <= line_num <= len(lines):
                        youtuber_to_remove = lines[line_num - 1]
                    else:
                        youtuber_to_remove = lines[-1]  # Remove last one if cursor is at end
            except tk.TclError:
                # If no selection and can't get cursor position, remove the last one
                youtuber_to_remove = lines[-1]

            if youtuber_to_remove in lines:
                # Remove from lines and update internal list
                lines.remove(youtuber_to_remove)
                self.youtubers = lines

                # Update the text widget
                updated_text = '\n'.join(self.youtubers)
                self.youtuber_text.delete('1.0', tk.END)
                self.youtuber_text.insert('1.0', updated_text)

                # Save to file
                save_youtuber_list(self.youtubers)
                self.status_var.set(f"Removed YouTuber: {youtuber_to_remove}")
            else:
                self.status_var.set("Selected YouTuber not found in list")

        except Exception as e:
            self.status_var.set(f"Error removing YouTuber: {str(e)}")
    
    def refresh_data(self):
        # Sync the youtuber list from the text widget in case user edited it directly
        self.sync_youtuber_list()

        # Show loading status
        self.status_var.set("Starting data fetch in background...")
        self.root.update()
        
        # Create a progress queue for communication between threads
        self.progress_queue = queue.Queue()
        
        # Start a background thread for data fetching and image generation
        threading.Thread(target=self.background_process, daemon=True).start()
        
        # Start checking the queue periodically
        self.root.after(100, self.check_progress_queue)
    
    def check_progress_queue(self):
        """Check for messages from the background thread"""
        try:
            while True:  # Process all available messages
                message = self.progress_queue.get_nowait()
                
                # Handle different message types
                if message['type'] == 'status':
                    self.status_var.set(message['text'])
                elif message['type'] == 'complete':
                    self.status_var.set(message['text'])
                    if message.get('image_path'):
                        self.current_composite_path = message['image_path']
                        self.display_image(message['image_path'])
                elif message['type'] == 'error':
                    self.status_var.set(f"Error: {message['text']}")
                    
                self.progress_queue.task_done()
        except queue.Empty:
            # Queue is empty, check again later
            pass
        finally:
            # Schedule the next check
            self.root.after(100, self.check_progress_queue)
    
    def background_process(self):
        """Background thread to fetch data and generate image"""
        try:
            # Fetch data
            self.progress_queue.put({'type': 'status', 'text': 'Fetching video data...'})
            video_details = self.fetch_data_bg()
            
            if video_details:
                # Create image with fetched data
                self.progress_queue.put({'type': 'status', 'text': 'Generating image...'})
                image_path = self.create_daily_composite_image_bg(video_details)

                if image_path:
                    self.progress_queue.put({
                        'type': 'complete',
                        'text': f"Created image with {len(video_details)} videos",
                        'image_path': image_path
                    })
                else:
                    self.progress_queue.put({'type': 'error', 'text': 'Failed to create image'})
            else:
                # No videos fetched, try to use cached data from any available YouTubers
                self.progress_queue.put({'type': 'status', 'text': 'No new videos fetched, trying to use cached data...'})
                cached_video_details = self.load_cached_video_data()

                if cached_video_details:
                    # Generate new image with cached data and current settings
                    self.progress_queue.put({'type': 'status', 'text': 'Generating image with cached data...'})
                    image_path = self.create_daily_composite_image_bg(cached_video_details)

                    if image_path:
                        self.progress_queue.put({
                            'type': 'complete',
                            'text': f'Created image with cached data ({len(cached_video_details)} videos)',
                            'image_path': image_path
                        })
                        return
                    else:
                        self.progress_queue.put({'type': 'error', 'text': 'Failed to create image with cached data'})
                else:
                    # Check if YouTuber list is empty
                    if len(self.youtubers) == 0:
                        self.progress_queue.put({'type': 'error', 'text': 'No YouTubers in list. Please add some YouTubers first.'})
                    else:
                        self.progress_queue.put({'type': 'error', 'text': 'No videos found. Please check your YouTuber list or try force fetch.'})
                
        except Exception as e:
            self.progress_queue.put({'type': 'error', 'text': str(e)})

    def get_day_dominant_color(self, videos):
        """Get the dominant color from all thumbnails in a day"""
        try:
            all_colors = []
            for video in videos:
                try:
                    img = get_cached_image(video['video_id'], video['thumbnail_url'])
                    img = remove_black_borders(img)
                    dominant_color = get_dominant_color(img)
                    all_colors.append(dominant_color)
                except Exception as e:
                    print(f"Error getting dominant color for video {video['video_id']}: {e}")
                    continue
            
            if not all_colors:
                return (255, 255, 255)  # Default white
            
            # Average all dominant colors
            avg_r = sum(color[0] for color in all_colors) // len(all_colors)
            avg_g = sum(color[1] for color in all_colors) // len(all_colors)
            avg_b = sum(color[2] for color in all_colors) // len(all_colors)
            
            return (avg_r, avg_g, avg_b)
        except Exception as e:
            print(f"Error getting day dominant color: {e}")
            return (255, 255, 255)  # Default white

    def get_day_green_red_color(self, videos):
        """Determine if a day is more green or red based on thumbnails"""
        try:
            green_count = 0
            red_count = 0
            neutral_count = 0
            
            for video in videos:
                try:
                    img = get_cached_image(video['video_id'], video['thumbnail_url'])
                    img = remove_black_borders(img)
                    color_type = get_green_red_ratio(img)
                    print(f"  Video {video['video_id'][:8]}...: {color_type}")
                    if color_type == 'green':
                        green_count += 1
                    elif color_type == 'red':
                        red_count += 1
                    else:  # neutral
                        neutral_count += 1
                except Exception as e:
                    print(f"Error analyzing green/red for video {video['video_id']}: {e}")
                    continue
            
            total_videos = len(videos)
            if total_videos == 0:
                return (200, 200, 200)  # Default gray
            
            # Calculate percentages
            green_percentage = green_count / total_videos
            red_percentage = red_count / total_videos
            neutral_percentage = neutral_count / total_videos
            
            # More lenient thresholds for better detection
            # Green needs at least 30% of videos and to be 15% more than red
            if green_percentage >= 0.3 and green_percentage > red_percentage + 0.15:
                return (0, 255, 0)  # Green
            elif red_percentage >= 0.3 and red_percentage > green_percentage + 0.15:
                return (255, 0, 0)  # Red
            else:
                # If no clear majority, return a color based on the mix
                if green_count > red_count:
                    # More green than red, but not enough for pure green
                    return (128, 255, 128)  # Light green
                elif red_count > green_count:
                    # More red than green, but not enough for pure red
                    return (255, 128, 128)  # Light red
                else:
                    # Equal or mostly neutral
                    return (200, 200, 200)  # Gray
                    
        except Exception as e:
            print(f"Error getting day green/red color: {e}")
            return (200, 200, 200)  # Default gray

    def load_cached_video_data(self):
        """Load cached video data from metadata files"""
        try:
            cached_video_details = []
            # Use the same limit as configured in the UI
            try:
                videos_per_channel = int(self.limit_var.get())
            except ValueError:
                videos_per_channel = 10  # Default if invalid input

            self.progress_queue.put({'type': 'status', 'text': f'Loading cached data for {len(self.youtubers)} YouTubers...'})

            for youtuber_name in self.youtubers:
                try:
                    # Load cached metadata for this YouTuber
                    metadata_path = os.path.join(METADATA_DIR, f"{youtuber_name}_videos.json")

                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            youtuber_videos = json.load(f)

                        # Take only the most recent videos (up to videos_per_channel limit)
                        for video_data in youtuber_videos[:videos_per_channel]:
                            cached_video_details.append({
                                'title': video_data.get('title', ''),
                                'thumbnail_url': video_data.get('thumbnail_url', ''),
                                'published_at': video_data.get('published_at', 0),
                                'video_id': video_data.get('video_id', ''),
                                'channel': youtuber_name,
                                'view_count': video_data.get('view_count', 0)
                            })

                        self.progress_queue.put({'type': 'status', 'text': f'Loaded {len(youtuber_videos[:videos_per_channel])} cached videos for {youtuber_name}'})

                except Exception as e:
                    self.progress_queue.put({'type': 'status', 'text': f'Warning: Could not load cached data for {youtuber_name}: {str(e)}'})
                    continue

            if cached_video_details:
                # Sort by publication date (newest first)
                cached_video_details = sorted(cached_video_details, key=lambda x: x['published_at'], reverse=True)
                self.progress_queue.put({'type': 'status', 'text': f'Successfully loaded {len(cached_video_details)} cached videos total'})
                return cached_video_details
            else:
                self.progress_queue.put({'type': 'status', 'text': 'No cached video data found'})
                return None

        except Exception as e:
            self.progress_queue.put({'type': 'error', 'text': f'Error loading cached video data: {str(e)}'})
            return None

    def fetch_data_bg(self):
        """Background version of fetch_data that doesn't update UI directly"""
        try:
            # List to hold video details
            video_details = []
            
            # Get videos per channel limit from input field
            try:
                videos_per_channel = int(self.limit_var.get())
            except ValueError:
                videos_per_channel = 10  # Default if invalid input
            
            # Fetch videos from each YouTuber
            youtuber_index = 0
            total_youtubers = len(self.youtubers)
            force_fetch_enabled = self.force_fetch.get()
            skipped_count = 0
            youtuber_video_cache = {}  # Store videos for caching

            for channel_username in self.youtubers:
                try:
                    # Check how many videos are already cached for this YouTuber
                    cached_video_count = 0
                    metadata_path = os.path.join(METADATA_DIR, f"{channel_username}_videos.json")
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                cached_videos = json.load(f)
                            cached_video_count = len(cached_videos)
                        except Exception:
                            cached_video_count = 0

                    # Determine if we need to fetch more videos
                    videos_to_fetch = max(0, videos_per_channel - cached_video_count)

                    if videos_to_fetch > 0 and (should_fetch_youtuber(channel_username, force_fetch_enabled) or cached_video_count < videos_per_channel):
                        if cached_video_count > 0:
                            self.progress_queue.put({'type': 'status', 'text': f"({youtuber_index}/{total_youtubers})Fetching {videos_to_fetch} additional videos for {channel_username} ({cached_video_count} cached)..."})
                        else:
                            self.progress_queue.put({'type': 'status', 'text': f"({youtuber_index}/{total_youtubers})Fetching videos for {channel_username}..."})
                        videos = scrapetube.get_channel(channel_username=channel_username)

                        # Load existing cached videos if any
                        youtuber_videos = []
                        if cached_video_count > 0:
                            try:
                                with open(metadata_path, 'r', encoding='utf-8') as f:
                                    youtuber_videos = json.load(f)
                            except Exception:
                                youtuber_videos = []

                        # We'll fetch videos until we reach videos_per_channel total
                    else:
                        self.progress_queue.put({'type': 'status', 'text': f"({youtuber_index}/{total_youtubers})Skipping {channel_username} (sufficient videos cached)"})
                        skipped_count += 1
                        youtuber_index += 1
                        continue

                    index = len(youtuber_videos)  # Start from where we left off
                    videos_processed = 0
                    for video in videos:
                        # Check if we already have enough total videos (cached + newly processed)
                        if len(youtuber_videos) >= videos_per_channel:
                            break
                        video_id = video['videoId']
                        title = video['title']
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                        
                        # Update status every few videos
                        self.progress_queue.put({'type': 'status', 'text': f"({youtuber_index}/{total_youtubers}) Fetching {channel_username}: {len(youtuber_videos)}/{videos_per_channel}"})

                        # Get publication date and view count
                        published_at = get_video_pubdate(video_id, video_url)
                        if published_at:
                            published_at = convert_to_unix_timestamp(published_at)
                            view_count = get_video_view_count(video_id, video_url) or 0

                            # Only add if this video isn't already in our cache
                            video_exists = any(v['video_id'] == video_id for v in youtuber_videos)
                            if not video_exists:
                                youtuber_videos.append({
                                    'title': title,
                                    'thumbnail_url': thumbnail_url,
                                    'published_at': published_at,
                                    'video_id': video_id,
                                    'view_count': view_count
                                })

                                # Also add to video_details for immediate use
                                video_details.append({
                                    'title': title,
                                    'thumbnail_url': thumbnail_url,
                                    'published_at': published_at,
                                    'video_id': video_id,
                                    'channel': channel_username,
                                    'view_count': view_count
                                })
                                videos_processed += 1

                                # Break if we've reached the target count after adding this video
                                if len(youtuber_videos) >= videos_per_channel:
                                    break

                    # Save to cache file
                    if youtuber_videos:
                        cache_path = os.path.join(METADATA_DIR, f"{channel_username}_videos.json")
                        try:
                            with open(cache_path, 'w', encoding='utf-8') as f:
                                json.dump(youtuber_videos, f, indent=2, ensure_ascii=False)
                        except Exception as e:
                            print(f"Error saving video cache for {channel_username}: {e}")

                    # Update fetch cache for successful fetch
                    update_fetch_cache(channel_username)
                    total_videos = len(youtuber_videos)
                    if videos_processed > 0:
                        if cached_video_count > 0:
                            self.progress_queue.put({'type': 'status', 'text': f"Updated {channel_username}: {total_videos} total videos ({cached_video_count} cached + {videos_processed} new)"})
                        else:
                            self.progress_queue.put({'type': 'status', 'text': f"Fetched {total_videos} videos for {channel_username}"})
                    else:
                        self.progress_queue.put({'type': 'status', 'text': f"Using cached videos for {channel_username} ({total_videos} videos)"})
                except Exception as e:
                    print(f"Error fetching videos for {channel_username}")
                    self.progress_queue.put({'type': 'status', 'text': f"⚠️ Could not fetch {channel_username}"})
                    # Continue with next YouTuber instead of stopping
                youtuber_index += 1
            # Sort videos by publication date (newest first)
            video_details = sorted(video_details, key=lambda x: x['published_at'], reverse=True)

            fetched_count = total_youtubers - skipped_count
            failed_count = total_youtubers - skipped_count - len([v for v in video_details if v['channel'] in self.youtubers])
            
            if len(video_details) > 0:
                if force_fetch_enabled:
                    self.progress_queue.put({'type': 'status', 'text': f"Force fetched {fetched_count} YouTubers, got {len(video_details)} videos total"})
                else:
                    self.progress_queue.put({'type': 'status', 'text': f"Fetched {fetched_count} YouTubers (skipped {skipped_count} cached), got {len(video_details)} videos total"})
            else:
                self.progress_queue.put({'type': 'status', 'text': f"No videos fetched from {total_youtubers} YouTubers (will try cached data)"})

            return video_details
                
        except Exception as e:
            print(f"Error in fetch_data_bg: {e}")
            self.progress_queue.put({'type': 'status', 'text': f"Error fetching data: {e}"})
            return []
    
    def create_daily_composite_image_bg(self, video_details):
        """Background version of create_daily_composite_image that works with provided video details"""
        try:
            if not video_details:
                self.progress_queue.put({'type': 'status', 'text': "No videos to display"})
                return None
            
            # Get days to display from input field
            try:
                days_to_display = int(self.days_var.get())
            except ValueError:
                days_to_display = 7  # Default if invalid input
            
            # Group videos by day
            videos_by_day = {}
            
            # Get the current date as the reference point
            latest_timestamp = max(video['published_at'] for video in video_details)
            latest_date = pd.to_datetime(latest_timestamp, unit='ms').date()
            
            # Create day buckets for the last N days
            for i in range(days_to_display):
                day = latest_date - timedelta(days=i)
                videos_by_day[day] = []
            
            # Assign videos to day buckets
            for video in video_details:
                video_date = pd.to_datetime(video['published_at'], unit='ms').date()
                if video_date in videos_by_day:
                    videos_by_day[video_date].append(video)
            
            # Sort days in chronological order (oldest first)
            # We'll draw them from right to left, so the newest will be on the left
            sorted_days = sorted(videos_by_day.keys())
            
            # Analyze colors for each day if needed
            day_colors = {}
            color_option = self.color_option.get()
            
            if color_option in ["dominant", "green_red"]:
                self.progress_queue.put({'type': 'status', 'text': 'Analyzing thumbnail colors...'})
                for day in sorted_days:
                    videos = videos_by_day[day]
                    if videos:
                        if color_option == "dominant":
                            # Get dominant color from all thumbnails in this day
                            day_colors[day] = self.get_day_dominant_color(videos)
                        elif color_option == "green_red":
                            # Determine if day is more green or red
                            print(f"\nAnalyzing day {day} with {len(videos)} videos:")
                            day_colors[day] = self.get_day_green_red_color(videos)
                            print(f"Day {day}: Final color: {day_colors[day]}")
                    else:
                        day_colors[day] = (255, 255, 255)  # Default white
            
            # Calculate the maximum number of thumbnails in a day
            max_thumbnails = max(len(videos_by_day[day]) for day in sorted_days) if sorted_days else 0
            
            if max_thumbnails == 0:
                self.progress_queue.put({'type': 'status', 'text': "No videos found in the selected date range"})
                return None
            
            # Get a sample thumbnail to determine dimensions
            sample_video = video_details[0]
            sample_img = get_cached_image(sample_video['video_id'], sample_video['thumbnail_url'])
            
            # Remove any black borders from the sample image first
            sample_img = remove_black_borders(sample_img)
            
            # Base dimensions
            base_width = 320  # Base YouTube thumbnail width
            base_height = int(base_width * (sample_img.height / sample_img.width))
            
            # Get sizing option
            sizing_option = self.sizing_option.get()
            
            # Calculate dimensions based on sizing option
            if sizing_option == "1":  # Column width by total views per day
                # Calculate total views for each day
                day_total_views = {}
                for day in sorted_days:
                    day_total_views[day] = sum(video['view_count'] for video in videos_by_day[day])
                
                # Find max total views to normalize
                max_total_views = max(day_total_views.values()) if day_total_views else 1
                
                # Calculate column widths based on total views
                column_widths = {}
                for day in sorted_days:
                    if max_total_views > 0:
                        ratio = day_total_views[day] / max_total_views
                        column_widths[day] = max(int(base_width * ratio), base_width // 2)  # Minimum half width
                    else:
                        column_widths[day] = base_width
                
                # For variable width columns, thumbnails will be sized to fit column width
                # We'll calculate height based on the base aspect ratio
                thumbnail_width = base_width  # This is just a reference, actual width will be col_width
                thumbnail_height = base_height  # This is just a reference, actual height will be proportional
                canvas_width = sum(column_widths.values())

            elif sizing_option == "2":  # Column width by average views per day
                # Calculate average views for each day
                day_avg_views = {}
                for day in sorted_days:
                    videos_in_day = videos_by_day[day]
                    if videos_in_day:
                        day_avg_views[day] = sum(video['view_count'] for video in videos_in_day) / len(videos_in_day)
                    else:
                        day_avg_views[day] = 0
                
                # Find max average views to normalize
                max_avg_views = max(day_avg_views.values()) if day_avg_views else 1
                
                # Calculate column widths based on average views
                column_widths = {}
                for day in sorted_days:
                    if max_avg_views > 0:
                        ratio = day_avg_views[day] / max_avg_views
                        column_widths[day] = max(int(base_width * ratio), base_width // 2)  # Minimum half width
                    else:
                        column_widths[day] = base_width
                
                thumbnail_width = base_width
                thumbnail_height = base_height
                canvas_width = sum(column_widths.values())
                
            elif sizing_option == "3":  # Thumbnail size by views (same day)
                # Calculate max views for each day to normalize within that day
                day_max_views = {}
                for day in sorted_days:
                    videos_in_day = videos_by_day[day]
                    if videos_in_day:
                        day_max_views[day] = max(video['view_count'] for video in videos_in_day)
                    else:
                        day_max_views[day] = 1
                
                # All columns have same width, but thumbnails vary in size
                column_widths = {day: base_width for day in sorted_days}
                thumbnail_width = base_width
                thumbnail_height = base_height
                canvas_width = len(sorted_days) * base_width
                
            elif sizing_option == "4":  # Thumbnail size by views (all days)
                # Calculate max views across all videos to normalize
                all_max_views = max(video['view_count'] for video in video_details) if video_details else 1
                
                # All columns have same width, but thumbnails vary in size
                column_widths = {day: base_width for day in sorted_days}
                thumbnail_width = base_width
                thumbnail_height = base_height
                canvas_width = len(sorted_days) * base_width
                
            else:  # Default (fixed size)
                # Use fixed dimensions for all thumbnails
                column_widths = {day: base_width for day in sorted_days}
                thumbnail_width = base_width
                thumbnail_height = base_height
                canvas_width = len(sorted_days) * base_width
            
            # Calculate canvas height
            header_height = 60  # Increased height for day header to accommodate larger font

            if sizing_option in ["1", "2"]:  # Variable column widths
                # For variable widths, calculate height based on the widest column
                max_column_width = max(column_widths.values())
                max_thumbnail_height = int(max_column_width * (base_height / base_width))
                canvas_height = max_thumbnails * max_thumbnail_height + header_height
            else:
                # For fixed widths, use standard height
                canvas_height = max_thumbnails * thumbnail_height + header_height
            
            # Create a blank canvas with pure white background
            composite = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))
            draw = ImageDraw.Draw(composite)
            
            # Try to load a font with larger size for column headers, fall back to default if not available
            try:
                font = ImageFont.truetype("arial.ttf", 32)  # Increased font size from 20 to 32
            except IOError:
                font = ImageFont.load_default()
            
            # Draw day columns (newest to oldest from left to right)
            total_columns = len(sorted_days)
            current_x = 0  # Track current x position for variable column widths

            # Handle day order based on checkbutton setting
            if self.reverse_days_order.get():
                # Checkbox checked: oldest to newest
                drawing_days = sorted_days  # sorted_days is oldest first
            else:
                # Checkbox unchecked: newest to oldest (default)
                drawing_days = list(reversed(sorted_days))  # Reverse to get newest first

            for idx, day in enumerate(drawing_days):
                # Calculate column position for fixed width layouts
                col_idx = total_columns - 1 - idx
                
                # Get column width for this day
                col_width = column_widths[day]
                
                # Calculate column position based on sizing option
                if sizing_option in ["1", "2"]:  # Variable column widths
                    # For variable widths, we need to calculate position from left to right
                    # since we're building the canvas from left to right
                    col_x = current_x
                    current_x += col_width
                else:  # Fixed column widths
                    col_x = col_idx * base_width
                
                # Draw day header with abbreviated month format
                day_str = day.strftime("%d %b %Y")  # Format like "15 Apr 2023"
                
                # Determine header background color based on color option
                if color_option == "default":
                    header_color = (200, 200, 200)  # Default gray
                elif color_option == "dominant" and day in day_colors:
                    header_color = day_colors[day]
                elif color_option == "green_red" and day in day_colors:
                    header_color = day_colors[day]
                else:
                    header_color = (200, 200, 200)  # Default gray
                
                draw.rectangle([col_x, 0, col_x + col_width, header_height], 
                              fill=header_color, outline=None)
                
                # Center the text in the header both horizontally and vertically
                # Use getbbox for modern Pillow versions
                try:
                    bbox = font.getbbox(day_str)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                except AttributeError:
                    # Fallback for older Pillow versions
                    try:
                        text_width, text_height = font.getsize(day_str)
                    except AttributeError:
                        # Final fallback - estimate dimensions
                        text_width = len(day_str) * 12  # Rough estimate
                        text_height = 32
                
                text_x = col_x + (col_width - text_width) // 2
                text_y = (header_height - text_height) // 2
                
                # Determine text color based on background brightness
                if color_option == "default":
                    text_color = (0, 0, 0)  # Black text on gray background
                else:
                    # Calculate brightness of background color
                    brightness = sum(header_color) / 3
                    if brightness > 128:  # Light background
                        text_color = (0, 0, 0)  # Black text
                    else:  # Dark background
                        text_color = (255, 255, 255)  # White text
                
                draw.text((text_x, text_y), day_str, fill=text_color, font=font)

                # Draw vertical line after this column (except for the last column)
                if self.draw_vertical_lines.get() and idx < len(drawing_days) - 1:
                    if sizing_option in ["1", "2"]:  # Variable column widths
                        line_x = col_x + col_width
                    else:  # Fixed column widths
                        line_x = col_x + base_width
                    draw.line([line_x, 0, line_x, canvas_height], fill=(100, 100, 100), width=2)

                # Draw thumbnails for this day
                videos = videos_by_day[day]

                # For variable column widths, calculate the thumbnail height for this column
                if sizing_option in ["1", "2"]:
                    column_thumbnail_height = int(col_width * (base_height / base_width))

                for row_idx, video in enumerate(videos):
                    # Calculate thumbnail position
                    if sizing_option in ["1", "2"]:  # Variable column widths
                        # For variable widths, all thumbnails in a column have the same size
                        # so we can use standard row positioning
                        thumb_y = header_height + row_idx * column_thumbnail_height
                    else:
                        # For fixed widths, use standard row positioning
                        thumb_y = header_height + row_idx * thumbnail_height
                    
                    # Get the thumbnail and remove black borders
                    img = get_cached_image(video['video_id'], video['thumbnail_url'])
                    
                    # Calculate thumbnail size based on sizing option
                    if sizing_option == "1" or sizing_option == "2":  # Variable column widths
                        # For variable width columns, force fit thumbnail to column width
                        thumb_width = col_width
                        thumb_height = column_thumbnail_height  # Use the pre-calculated height
                    elif sizing_option == "3":  # Thumbnail size by views (same day)
                        # Normalize within the same day
                        day_max = day_max_views[day]
                        if day_max > 0:
                            ratio = video['view_count'] / day_max
                            thumb_width = max(int(base_width * ratio), base_width // 4)  # Minimum quarter width
                            thumb_height = int(thumb_width * (base_height / base_width))
                            # Ensure thumbnail doesn't exceed column width
                            if thumb_width > col_width:
                                thumb_width = col_width
                                thumb_height = int(thumb_width * (base_height / base_width))
                        else:
                            thumb_width, thumb_height = col_width, int(col_width * (base_height / base_width))
                    elif sizing_option == "4":  # Thumbnail size by views (all days)
                        # Normalize across all videos
                        if all_max_views > 0:
                            ratio = video['view_count'] / all_max_views
                            thumb_width = max(int(base_width * ratio), base_width // 4)  # Minimum quarter width
                            thumb_height = int(thumb_width * (base_height / base_width))
                            # Ensure thumbnail doesn't exceed column width
                            if thumb_width > col_width:
                                thumb_width = col_width
                                thumb_height = int(thumb_width * (base_height / base_width))
                        else:
                            thumb_width, thumb_height = col_width, int(col_width * (base_height / base_width))
                    else:  # Option 5: Fixed size thumbnails
                        thumb_width, thumb_height = thumbnail_width, thumbnail_height

                    # Resize thumbnail if needed
                    if img.width != thumb_width or img.height != thumb_height:
                        img = img.resize((thumb_width, thumb_height), Image.LANCZOS)

                    # Center thumbnail in column
                    thumb_x = col_x + (col_width - thumb_width) // 2
                    
                    # Paste the thumbnail onto the canvas
                    composite.paste(img, (thumb_x, thumb_y))
                    
                    # Update progress every few thumbnails
                    if (idx * max_thumbnails + row_idx) % 10 == 0:
                        self.progress_queue.put({'type': 'status', 'text': f"Processing thumbnails: {idx * max_thumbnails + row_idx}/{len(sorted_days) * max_thumbnails}"})
            
            # Add timestamp and save
            timestamp = int(time.time())
            composite_path = os.path.join(COMPOSITE_DIR, f"daily_{timestamp}.png")
            composite.save(composite_path)
            
            # Return the path to the created image
            return composite_path
        
        except Exception as e:
            print(f"Error creating daily composite image: {e}")
            self.progress_queue.put({'type': 'status', 'text': f"Error creating daily composite image: {e}"})
            return None
    
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
    print("Starting YouTube Thumbnails by Day application...")
    app = DailyThumbnailApp()
    print("Initialization complete, running application...")
    app.run()