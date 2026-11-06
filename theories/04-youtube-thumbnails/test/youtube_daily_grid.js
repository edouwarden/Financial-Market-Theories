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


// Configuration des délais
const REQUEST_DELAY = 1000; // 1 seconde entre les requêtes

/**
 * Récupérer la dernière vidéo d'un YouTuber
 */
async function getLatestVideo(youtuberName) {
	try {
		console.log(`Récupération vidéos pour ${youtuberName}...`);

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
		console.log(`Erreur récupération vidéo pour ${youtuberName}: ${e.message}`);
		return null;
	}
}

/**
 * Récupérer toutes les vidéos du jour
 */
async function getTodayVideos() {
	const todayVideos = [];

	console.log(`Récupération des vidéos pour ${YOUTUBERS.length} YouTubers...`);

	for (let i = 0; i < YOUTUBERS.length; i++) {
		const youtuber = YOUTUBERS[i];

		try {
			const video = await getLatestVideo(youtuber);
			if (video && video.uploadDate && !video.uploadDate.includes("day") && !video.uploadDate.includes("days") && !video.uploadDate.includes("week") && !video.uploadDate.includes("weeks"))
				todayVideos.push(video);
			if (i < YOUTUBERS.length - 1) 
				await new Promise(resolve => setTimeout(resolve, REQUEST_DELAY));
		} catch (e) {
			console.log(`Erreur pour ${youtuber}: ${e.message}`);
		}
	}
	return todayVideos;
}

/**
 * Créer une grille d'images
 */
async function createImageGrid(videos) {
	if (videos.length === 0) {
		console.log("Aucune vidéo du jour trouvée");
		return null;
	}

	// Calculer les dimensions de la grille
	const cols = Math.ceil(Math.sqrt(videos.length));
	const rows = Math.ceil(videos.length / cols);

	// Dimensions des thumbnails
	const thumbnailWidth = 168;
	const thumbnailHeight = 94;
	const padding = 0;
	const titleHeight = 0;

	// Dimensions du canvas
	const canvasWidth = cols * (thumbnailWidth + padding) + padding;
	const canvasHeight = rows * (thumbnailHeight + titleHeight + padding) + padding;

	// Créer le canvas
	const canvas = createCanvas(canvasWidth, canvasHeight);
	const ctx = canvas.getContext('2d');

	// Fond blanc
	ctx.fillStyle = '#ffffff';
	ctx.fillRect(0, 0, canvasWidth, canvasHeight);

	// Charger et dessiner chaque thumbnail
	for (let i = 0; i < videos.length; i++) {
		const video = videos[i];
		const row = Math.floor(i / cols);
		const col = i % cols;

		const x = col * (thumbnailWidth + padding) + padding;
		const y = row * (thumbnailHeight + titleHeight + padding) + padding;

		try {
			// Charger l'image
			const img = await loadImage(video.thumbnail.url);

			// Dessiner le thumbnail
			ctx.drawImage(img, x, y, thumbnailWidth, thumbnailHeight);

			// Dessiner le titre (tronqué)
			//ctx.fillStyle = '#000000';
			//ctx.font = '14px Arial';
			//const title = video.title.length > 40 ? video.title.substring(0, 40) + '...' : video.title;
			//ctx.fillText(title, x, y + thumbnailHeight + 20);

			// Dessiner le nom du channel
			//ctx.fillStyle = '#666666';
			//ctx.font = '12px Arial';
			//ctx.fillText(video.channel, x, y + thumbnailHeight + 35);

			console.log(`✓ Thumbnail ${i + 1}/${videos.length} dessiné`);

		} catch (e) {
			console.log(`Erreur chargement image pour ${video.thumbnail}: ${e.message}`);

			// Dessiner un rectangle gris en cas d'erreur
			ctx.fillStyle = '#cccccc';
			ctx.fillRect(x, y, thumbnailWidth, thumbnailHeight);
			ctx.fillStyle = '#000000';
			ctx.font = '14px Arial';
			ctx.fillText('Erreur chargement', x, y + thumbnailHeight / 2);
		}
	}
	const buffer = canvas.toBuffer('image/png');
	return buffer;
}

/**
 * Fonction principale
 */
async function main() {
	try {
		console.log("=== YouTube Daily Grid Generator ===");

		// Récupérer les vidéos du jour
		const todayVideos = await getTodayVideos();
		if (todayVideos.length === 0) {
			console.log("Aucune vidéo publiée aujourd'hui trouvée.");
			return;
		}

		console.log(`\n${todayVideos.length} vidéos du jour trouvées:`);

		// Créer la grille
		const grid = await createImageGrid(todayVideos);

				

	} catch (e) {
		console.error("Erreur dans le script principal:", e);
	}
}

// Exécuter le script
if (require.main === module) {
	main();
}

