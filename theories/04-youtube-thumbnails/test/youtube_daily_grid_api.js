const fs = require('fs');
const path = require('path');
const https = require('https');
const { createCanvas, loadImage } = require('canvas');

// Configuration
const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY || 'YOUR_API_KEY_HERE';
const YOUTUBERS = [
	"CoinBureau",
	"AltcoinDaily",
	"TheBitBoyX",
	"CryptosRUs",
	"99Bitcoins",
	"EllioTradesCrypto",
	"VoskCoin",
	"TheMoon",
	"TheCryptoLark",
	"davincij15",
	"IvanonTech",
	"DataDash",
	"Boxmining",
	"MMCrypto",
	"AlessioRastani",
	"aantonop",
	"ChicoCrypto",
	"BTCSessions",
	"CryptoZombie",
	"CryptoLove",
	"TheModernInvestor",
	"CryptoTips",
	"chrisdunntv",
	"Hashoshi",
	"CryptoDaily",
	"CryptoKirbyTrading",
	"RichardHeart",
	"CryptoCrow",
	"CryptoJoker",
	"CryptoRevolutionChannel",
	"CryptoRevolutiontv",
	"ToneVays",
	"CryptoBobby",
	"Crypt0",
	"LouisThomas",
	"NuggetsNews",
	"ReadySet",
	"CobbXRP",
	"Philakone",
	"CryptoOracle",
	"DappUniversity",
	"HackCrypto",
	"Moocharoo",
	"Cryptonews",
	"NodeInvestor",
	"ScottMelker",
	"KeithWareing",
	"ThatMartiniGuy",
	"UndergroundTradingFr",
	"MrKristof",
	"Coffeezilla",
	"CryptoDecoded",
	"AltcoinAnalytics",
	"DeFiDaily1",
	"cherrytgbot",
	"CryptoVisionary",
	"MetaverseExplorer",
	"TokenTalks",
	"TheCryptoLab",
	"BlockchainBuilder",
	"CryptoInsiderOfficial",
	"YieldMaster",
	"BlockchainBasics",
	"CryptoDataHub",
	"CryptoPhilanthropist",
	"MarketPulseCrypto",
	"intothecryptoverse",
	"CryptoBanterGroup",
	"CryptoCasey",
	"DiscoverCrypto_",
	"kevinoleary",
	"Hasheur",
	"insydercrypto",
	"CryptoFutur",
	"BitcoinMagazine",
	"lesroisdubitcoin",
	"CryptoLeTrone",
	"grandanglebitcoin",
	"JulienRoman",
	"Cryptolyze",
	"MonsieurTK"
];

// Mapping of usernames to Channel IDs (required for the YouTube API)
const CHANNEL_IDS = {
	"CoinBureau": "UCqK_GSMbpiV8spgD3ZGloSw",
	"AltcoinDaily": "UC9lT9XdT6BjgC6YQ5e0wBzQ",
	"TheBitBoyX": "UCjemQfjaXAzA-95RKoy9n_g",
	"CryptosRUs": "UCI7M65p3Q-DQXi8g9w0iICg",
	"99Bitcoins": "UCnMngbHKG9c80Xvd1UjkM3w",
	"EllioTradesCrypto": "UCrYmtJBtLdtm2ov84ulV-yg",
	"VoskCoin": "UCaKZpnTTJQuh9-_i7Wr5KqA",
	"TheMoon": "UCvqJ9V1M3Fh0Km-K1Fop1Cw",
	"TheCryptoLark": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"davincij15": "UCqNCLd2r19wpWWQE6yDLOOQ",
	"IvanonTech": "UCrYmtJBtLdtm2ov84ulV-yg",
	"DataDash": "UC7mfnS9YeL-4yed1OXiGdCA",
	"Boxmining": "UCVpUZkH1Q3Iq5aEuB1i9GRQ",
	"MMCrypto": "UCB8l3k3Ff7e6U1KlaT_TX2g",
	"AlessioRastani": "UCqK_GSMbpiV8spgD3ZGloSw",
	"aantonop": "UCJWCJCWOxBYSi5DhCieLOLQ",
	"ChicoCrypto": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"BTCSessions": "UC9lT9XdT6BjgC6YQ5e0wBzQ",
	"CryptoZombie": "UCjemQfjaXAzA-95RKoy9n_g",
	"CryptoLove": "UCI7M65p3Q-DQXi8g9w0iICg",
	"TheModernInvestor": "UCnMngbHKG9c80Xvd1UjkM3w",
	"CryptoTips": "UCrYmtJBtLdtm2ov84ulV-yg",
	"chrisdunntv": "UCaKZpnTTJQuh9-_i7Wr5KqA",
	"Hashoshi": "UCvqJ9V1M3Fh0Km-K1Fop1Cw",
	"CryptoDaily": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"CryptoKirbyTrading": "UCqNCLd2r19wpWWQE6yDLOOQ",
	"RichardHeart": "UCrYmtJBtLdtm2ov84ulV-yg",
	"CryptoCrow": "UC7mfnS9YeL-4yed1OXiGdCA",
	"CryptoJoker": "UCVpUZkH1Q3Iq5aEuB1i9GRQ",
	"CryptoRevolutionChannel": "UCB8l3k3Ff7e6U1KlaT_TX2g",
	"CryptoRevolutiontv": "UCB8l3k3Ff7e6U1KlaT_TX2g",
	"ToneVays": "UCJWCJCWOxBYSi5DhCieLOLQ",
	"CryptoBobby": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"Crypt0": "UC9lT9XdT6BjgC6YQ5e0wBzQ",
	"LouisThomas": "UCjemQfjaXAzA-95RKoy9n_g",
	"NuggetsNews": "UCI7M65p3Q-DQXi8g9w0iICg",
	"ReadySet": "UCnMngbHKG9c80Xvd1UjkM3w",
	"CobbXRP": "UCrYmtJBtLdtm2ov84ulV-yg",
	"Philakone": "UCaKZpnTTJQuh9-_i7Wr5KqA",
	"CryptoOracle": "UCvqJ9V1M3Fh0Km-K1Fop1Cw",
	"DappUniversity": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"HackCrypto": "UCqNCLd2r19wpWWQE6yDLOOQ",
	"Moocharoo": "UCrYmtJBtLdtm2ov84ulV-yg",
	"Cryptonews": "UC7mfnS9YeL-4yed1OXiGdCA",
	"NodeInvestor": "UCVpUZkH1Q3Iq5aEuB1i9GRQ",
	"ScottMelker": "UCB8l3k3Ff7e6U1KlaT_TX2g",
	"KeithWareing": "UCJWCJCWOxBYSi5DhCieLOLQ",
	"ThatMartiniGuy": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"UndergroundTradingFr": "UC9lT9XdT6BjgC6YQ5e0wBzQ",
	"MrKristof": "UCjemQfjaXAzA-95RKoy9n_g",
	"Coffeezilla": "UCI7M65p3Q-DQXi8g9w0iICg",
	"CryptoDecoded": "UCnMngbHKG9c80Xvd1UjkM3w",
	"AltcoinAnalytics": "UCrYmtJBtLdtm2ov84ulV-yg",
	"DeFiDaily1": "UCaKZpnTTJQuh9-_i7Wr5KqA",
	"cherrytgbot": "UCvqJ9V1M3Fh0Km-K1Fop1Cw",
	"CryptoVisionary": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"MetaverseExplorer": "UCqNCLd2r19wpWWQE6yDLOOQ",
	"TokenTalks": "UCrYmtJBtLdtm2ov84ulV-yg",
	"TheCryptoLab": "UC7mfnS9YeL-4yed1OXiGdCA",
	"BlockchainBuilder": "UCVpUZkH1Q3Iq5aEuB1i9GRQ",
	"CryptoInsiderOfficial": "UCB8l3k3Ff7e6U1KlaT_TX2g",
	"YieldMaster": "UCJWCJCWOxBYSi5DhCieLOLQ",
	"BlockchainBasics": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"CryptoDataHub": "UC9lT9XdT6BjgC6YQ5e0wBzQ",
	"CryptoPhilanthropist": "UCjemQfjaXAzA-95RKoy9n_g",
	"MarketPulseCrypto": "UCI7M65p3Q-DQXi8g9w0iICg",
	"intothecryptoverse": "UCnMngbHKG9c80Xvd1UjkM3w",
	"CryptoBanterGroup": "UCrYmtJBtLdtm2ov84ulV-yg",
	"CryptoCasey": "UCaKZpnTTJQuh9-_i7Wr5KqA",
	"DiscoverCrypto_": "UCvqJ9V1M3Fh0Km-K1Fop1Cw",
	"kevinoleary": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"Hasheur": "UCqNCLd2r19wpWWQE6yDLOOQ",
	"insydercrypto": "UCrYmtJBtLdtm2ov84ulV-yg",
	"CryptoFutur": "UC7mfnS9YeL-4yed1OXiGdCA",
	"BitcoinMagazine": "UCVpUZkH1Q3Iq5aEuB1i9GRQ",
	"lesroisdubitcoin": "UCB8l3k3Ff7e6U1KlaT_TX2g",
	"CryptoLeTrone": "UCJWCJCWOxBYSi5DhCieLOLQ",
	"grandanglebitcoin": "UC2r5KIRhc7C5HD4OKjPhRAA",
	"JulienRoman": "UC9lT9XdT6BjgC6YQ5e0wBzQ",
	"Cryptolyze": "UCjemQfjaXAzA-95RKoy9n_g",
	"MonsieurTK": "UCI7M65p3Q-DQXi8g9w0iICg"
};

// Cache directories
const CACHE_DIR = "youtube_cache";
const COMPOSITE_DIR = "composite_images";
const METADATA_DIR = "youtube_metadata";

// Create the directories if they don't exist
[CACHE_DIR, COMPOSITE_DIR, METADATA_DIR].forEach(dir => {
	if (!fs.existsSync(dir)) {
		fs.mkdirSync(dir, { recursive: true });
	}
});

// Delay configuration
const REQUEST_DELAY = 1000; // 1 second between requests

/**
 * Utility function to make HTTPS requests
 */
function makeRequest(url) {
	return new Promise((resolve, reject) => {
		https.get(url, (response) => {
			let data = '';
			response.on('data', (chunk) => {
				data += chunk;
			});
			response.on('end', () => {
				try {
					const jsonData = JSON.parse(data);
					resolve(jsonData);
				} catch (e) {
					reject(new Error('Invalid JSON response'));
				}
			});
		}).on('error', (err) => {
			reject(err);
		});
	});
}

/**
 * Utility function to download an image
 */
function downloadImage(url, filepath) {
	return new Promise((resolve, reject) => {
		const file = fs.createWriteStream(filepath);
		https.get(url, (response) => {
			response.pipe(file);
			file.on('finish', () => {
				file.close();
				resolve();
			});
		}).on('error', (err) => {
			fs.unlink(filepath, () => { }); // Delete the file in case of error
			reject(err);
		});
	});
}

/**
 * Get the image from cache or download it
 */
async function getCachedImage(videoId, thumbnailUrl) {
	const cachePath = path.join(CACHE_DIR, `${videoId}.png`);

	if (fs.existsSync(cachePath)) {
		return await loadImage(cachePath);
	}

	// Download the image
	await downloadImage(thumbnailUrl, cachePath);
	return await loadImage(cachePath);
}

/**
 * Check whether a date falls on the current day (US time)
 */
function isTodayUS(publishedAt) {
	const now = new Date();
	const publishedDate = new Date(publishedAt);

	// Convert to US time (EST/EDT)
	const usTime = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
	const publishedUS = new Date(publishedDate.toLocaleString("en-US", { timeZone: "America/New_York" }));

	// Compare the dates (year, month, day)
	return usTime.getFullYear() === publishedUS.getFullYear() &&
		usTime.getMonth() === publishedUS.getMonth() &&
		usTime.getDate() === publishedUS.getDate();
}

/**
 * Get the metadata of a YouTube video via the API
 */
async function getVideoMetadata(videoId) {
	const metadataPath = path.join(METADATA_DIR, `${videoId}.json`);

	// Check the cache
	if (fs.existsSync(metadataPath)) {
		try {
			const cached = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
			if (cached.publishedAt && cached.viewCount !== undefined) {
				return cached;
			}
		} catch (e) {
			console.log(`Error reading cache for ${videoId}: ${e.message}`);
		}
	}

	// Get from the YouTube API
	try {
		const url = `https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id=${videoId}&key=${YOUTUBE_API_KEY}`;
		const data = await makeRequest(url);

		if (data.items && data.items.length > 0) {
			const video = data.items[0];
			const metadata = {
				publishedAt: video.snippet.publishedAt,
				viewCount: parseInt(video.statistics.viewCount) || 0
			};

			// Save to cache
			try {
				fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));
			} catch (e) {
				console.log(`Error saving cache for ${videoId}: ${e.message}`);
			}

			return metadata;
		}

		return { publishedAt: null, viewCount: 0 };
	} catch (e) {
		console.log(`Error fetching metadata for ${videoId}: ${e.message}`);
		return { publishedAt: null, viewCount: 0 };
	}
}

/**
 * Get the latest video from a YouTuber via the YouTube API
 */
async function getLatestVideo(youtuberName) {
	try {
		const channelId = CHANNEL_IDS[youtuberName];

		if (!channelId) {
			console.log(`Channel ID not found for ${youtuberName}`);
			return null;
		}

		console.log(`Fetching videos for ${youtuberName} (${channelId})...`);

		// Get the latest video from the channel
		const searchUrl = `https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=${channelId}&maxResults=1&order=date&type=video&key=${YOUTUBE_API_KEY}`;
		const searchData = await makeRequest(searchUrl);

		if (!searchData.items || searchData.items.length === 0) {
			console.log(`No video found for ${youtuberName}`);
			return null;
		}

		const video = searchData.items[0];
		const videoId = video.id.videoId;

		// Get the detailed metadata
		const metadata = await getVideoMetadata(videoId);

		return {
			videoId: videoId,
			title: video.snippet.title,
			thumbnailUrl: video.snippet.thumbnails.high.url,
			publishedAt: metadata.publishedAt,
			viewCount: metadata.viewCount,
			channel: youtuberName
		};

	} catch (e) {
		console.log(`Error fetching video for ${youtuberName}: ${e.message}`);
		return null;
	}
}

/**
 * Get all of today's videos
 */
async function getTodayVideos() {
	const todayVideos = [];

	console.log(`Fetching videos for ${YOUTUBERS.length} YouTubers...`);

	for (let i = 0; i < YOUTUBERS.length; i++) {
		const youtuber = YOUTUBERS[i];

		try {
			const video = await getLatestVideo(youtuber);

			if (video && video.publishedAt && isTodayUS(video.publishedAt)) {
				todayVideos.push(video);
				console.log(`✓ ${youtuber}: video from today found - "${video.title}"`);
			} else {
				console.log(`✗ ${youtuber}: no video from today`);
			}

			// Delay between requests to respect the API limits
			if (i < YOUTUBERS.length - 1) {
				await new Promise(resolve => setTimeout(resolve, REQUEST_DELAY));
			}

		} catch (e) {
			console.log(`Error for ${youtuber}: ${e.message}`);
		}
	}

	return todayVideos;
}

/**
 * Create a grid of images
 */
async function createImageGrid(videos) {
	if (videos.length === 0) {
		console.log("No video found for today");
		return null;
	}

	console.log(`Creating the grid with ${videos.length} videos...`);

	// Calculate the grid dimensions
	const cols = Math.ceil(Math.sqrt(videos.length));
	const rows = Math.ceil(videos.length / cols);

	// Thumbnail dimensions
	const thumbnailSize = 320;
	const padding = 10;
	const titleHeight = 40;

	// Canvas dimensions
	const canvasWidth = cols * (thumbnailSize + padding) + padding;
	const canvasHeight = rows * (thumbnailSize + titleHeight + padding) + padding;

	// Create the canvas
	const canvas = createCanvas(canvasWidth, canvasHeight);
	const ctx = canvas.getContext('2d');

	// White background
	ctx.fillStyle = '#ffffff';
	ctx.fillRect(0, 0, canvasWidth, canvasHeight);

	// Load and draw each thumbnail
	for (let i = 0; i < videos.length; i++) {
		const video = videos[i];
		const row = Math.floor(i / cols);
		const col = i % cols;

		const x = col * (thumbnailSize + padding) + padding;
		const y = row * (thumbnailSize + titleHeight + padding) + padding;

		try {
			// Load the image
			const img = await getCachedImage(video.videoId, video.thumbnailUrl);

			// Draw the thumbnail
			ctx.drawImage(img, x, y, thumbnailSize, thumbnailSize);

			// Draw the title (truncated)
			ctx.fillStyle = '#000000';
			ctx.font = 'bold 14px Arial';
			const title = video.title.length > 40 ? video.title.substring(0, 40) + '...' : video.title;
			ctx.fillText(title, x, y + thumbnailSize + 20);

			// Draw the channel name and the views
			ctx.fillStyle = '#666666';
			ctx.font = '12px Arial';
			const views = video.viewCount ? `${video.viewCount.toLocaleString()} views` : 'Unknown views';
			ctx.fillText(`${video.channel} • ${views}`, x, y + thumbnailSize + 35);

			console.log(`✓ Thumbnail ${i + 1}/${videos.length} drawn`);

		} catch (e) {
			console.log(`Error loading image for ${video.videoId}: ${e.message}`);

			// Draw a gray rectangle in case of error
			ctx.fillStyle = '#cccccc';
			ctx.fillRect(x, y, thumbnailSize, thumbnailSize);
			ctx.fillStyle = '#000000';
			ctx.font = '14px Arial';
			ctx.fillText('Loading error', x, y + thumbnailSize / 2);
		}
	}

	// Add a title at the top of the image
	ctx.fillStyle = '#000000';
	ctx.font = 'bold 24px Arial';
	const title = `Crypto Videos for ${new Date().toLocaleDateString('en-US', { timeZone: 'America/New_York' })} (${videos.length} videos)`;
	const titleWidth = ctx.measureText(title).width;
	ctx.fillText(title, (canvasWidth - titleWidth) / 2, 30);

	// Save the image
	const timestamp = Date.now();
	const outputPath = path.join(COMPOSITE_DIR, `daily_grid_${timestamp}.png`);

	const buffer = canvas.toBuffer('image/png');
	fs.writeFileSync(outputPath, buffer);

	console.log(`Grid saved: ${outputPath}`);
	return outputPath;
}

/**
 * Main function
 */
async function main() {
	try {
		console.log("=== YouTube Daily Grid Generator (API Version) ===");
		console.log(`Current date/time (US): ${new Date().toLocaleString("en-US", { timeZone: "America/New_York" })}`);

		if (YOUTUBE_API_KEY === 'YOUR_API_KEY_HERE') {
			console.log("⚠️  WARNING: Set your YouTube API key in the YOUTUBE_API_KEY environment variable");
			console.log("   Example: export YOUTUBE_API_KEY='your_api_key'");
			console.log("   Or edit the YOUTUBE_API_KEY variable directly in the script");
			return;
		}

		// Get today's videos
		const todayVideos = await getTodayVideos();

		if (todayVideos.length === 0) {
			console.log("No video published today was found.");
			return;
		}

		console.log(`\n${todayVideos.length} videos from today found:`);
		todayVideos.forEach(video => {
			console.log(`- ${video.channel}: ${video.title} (${video.viewCount.toLocaleString()} views)`);
		});

		// Create the grid
		const gridPath = await createImageGrid(todayVideos);

		if (gridPath) {
			console.log(`\n✅ Grid created successfully: ${gridPath}`);
		} else {
			console.log("\n❌ Error while creating the grid");
		}

	} catch (e) {
		console.error("Error in main script:", e);
	}
}

// Run the script
if (require.main === module) {
	main();
}

module.exports = {
	getTodayVideos,
	createImageGrid,
	isTodayUS,
	getLatestVideo
};
