const fs = require('fs');
const path = require('path');
const https = require('https');
const { Client } = require('youtubei');
const { createCanvas, loadImage } = require('canvas');

const youtube = new Client();
// Configuration
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


// Delay configuration
const REQUEST_DELAY = 1000; // 1 second between requests

/**
 * Get the latest video from a YouTuber
 */
async function getLatestVideo(youtuberName) {
	try {
		console.log(`Fetching videos for ${youtuberName}...`);

		const channel = await youtube.findOne(youtuberName, { type: "channel" });
		await channel.videos.next();
		const video = channel.videos.items[0];

		return {
			thumbnail: video.thumbnails[0],
			uploadDate: video.uploadDate,
			channel: youtuberName,
			views: video.viewCount
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
			if (video && video.uploadDate && !video.uploadDate.includes("day") && !video.uploadDate.includes("days") && !video.uploadDate.includes("week") && !video.uploadDate.includes("weeks"))
				todayVideos.push(video);
			if (i < YOUTUBERS.length - 1)
				await new Promise(resolve => setTimeout(resolve, REQUEST_DELAY));
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

	// Calculate the grid dimensions
	const cols = Math.ceil(Math.sqrt(videos.length));
	const rows = Math.ceil(videos.length / cols);

	// Thumbnail dimensions
	const thumbnailWidth = 168;
	const thumbnailHeight = 94;
	const padding = 0;
	const titleHeight = 0;

	// Canvas dimensions
	const canvasWidth = cols * (thumbnailWidth + padding) + padding;
	const canvasHeight = rows * (thumbnailHeight + titleHeight + padding) + padding;

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

		const x = col * (thumbnailWidth + padding) + padding;
		const y = row * (thumbnailHeight + titleHeight + padding) + padding;

		try {
			// Load the image
			const img = await loadImage(video.thumbnail.url);

			// Draw the thumbnail
			ctx.drawImage(img, x, y, thumbnailWidth, thumbnailHeight);

			// Draw the title (truncated)
			//ctx.fillStyle = '#000000';
			//ctx.font = '14px Arial';
			//const title = video.title.length > 40 ? video.title.substring(0, 40) + '...' : video.title;
			//ctx.fillText(title, x, y + thumbnailHeight + 20);

			// Draw the channel name
			//ctx.fillStyle = '#666666';
			//ctx.font = '12px Arial';
			//ctx.fillText(video.channel, x, y + thumbnailHeight + 35);

			console.log(`✓ Thumbnail ${i + 1}/${videos.length} drawn`);

		} catch (e) {
			console.log(`Error loading image for ${video.thumbnail}: ${e.message}`);

			// Draw a gray rectangle in case of error
			ctx.fillStyle = '#cccccc';
			ctx.fillRect(x, y, thumbnailWidth, thumbnailHeight);
			ctx.fillStyle = '#000000';
			ctx.font = '14px Arial';
			ctx.fillText('Loading error', x, y + thumbnailHeight / 2);
		}
	}
	const buffer = canvas.toBuffer('image/png');
	return buffer;
}

/**
 * Main function
 */
async function main() {
	try {
		console.log("=== YouTube Daily Grid Generator ===");

		// Get today's videos
		const todayVideos = await getTodayVideos();
		if (todayVideos.length === 0) {
			console.log("No video published today was found.");
			return;
		}

		console.log(`\n${todayVideos.length} videos from today found:`);

		// Create the grid
		const grid = await createImageGrid(todayVideos);



	} catch (e) {
		console.error("Error in main script:", e);
	}
}

// Run the script
if (require.main === module) {
	main();
}
