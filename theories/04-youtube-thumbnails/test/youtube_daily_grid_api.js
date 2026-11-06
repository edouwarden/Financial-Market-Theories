const fs = require('fs');
const path = require('path');
const https = require('https');
const { createCanvas, loadImage } = require('canvas');

// Configuration
const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY || 'VOTRE_CLE_API_ICI';
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

// Mapping des noms d'utilisateur vers les Channel IDs (nécessaire pour l'API YouTube)
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

// Dossiers de cache
const CACHE_DIR = "youtube_cache";
const COMPOSITE_DIR = "composite_images";
const METADATA_DIR = "youtube_metadata";

// Créer les dossiers s'ils n'existent pas
[CACHE_DIR, COMPOSITE_DIR, METADATA_DIR].forEach(dir => {
	if (!fs.existsSync(dir)) {
		fs.mkdirSync(dir, { recursive: true });
	}
});

// Configuration des délais
const REQUEST_DELAY = 1000; // 1 seconde entre les requêtes

/**
 * Fonction utilitaire pour faire des requêtes HTTPS
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
 * Fonction utilitaire pour télécharger une image
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
			fs.unlink(filepath, () => { }); // Supprimer le fichier en cas d'erreur
			reject(err);
		});
	});
}

/**
 * Obtenir l'image en cache ou la télécharger
 */
async function getCachedImage(videoId, thumbnailUrl) {
	const cachePath = path.join(CACHE_DIR, `${videoId}.png`);

	if (fs.existsSync(cachePath)) {
		return await loadImage(cachePath);
	}

	// Télécharger l'image
	await downloadImage(thumbnailUrl, cachePath);
	return await loadImage(cachePath);
}

/**
 * Vérifier si une date est dans la journée actuelle (heure US)
 */
function isTodayUS(publishedAt) {
	const now = new Date();
	const publishedDate = new Date(publishedAt);

	// Convertir en heure US (EST/EDT)
	const usTime = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
	const publishedUS = new Date(publishedDate.toLocaleString("en-US", { timeZone: "America/New_York" }));

	// Comparer les dates (année, mois, jour)
	return usTime.getFullYear() === publishedUS.getFullYear() &&
		usTime.getMonth() === publishedUS.getMonth() &&
		usTime.getDate() === publishedUS.getDate();
}

/**
 * Récupérer les métadonnées d'une vidéo YouTube via l'API
 */
async function getVideoMetadata(videoId) {
	const metadataPath = path.join(METADATA_DIR, `${videoId}.json`);

	// Vérifier le cache
	if (fs.existsSync(metadataPath)) {
		try {
			const cached = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
			if (cached.publishedAt && cached.viewCount !== undefined) {
				return cached;
			}
		} catch (e) {
			console.log(`Erreur lecture cache pour ${videoId}: ${e.message}`);
		}
	}

	// Récupérer depuis l'API YouTube
	try {
		const url = `https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id=${videoId}&key=${YOUTUBE_API_KEY}`;
		const data = await makeRequest(url);

		if (data.items && data.items.length > 0) {
			const video = data.items[0];
			const metadata = {
				publishedAt: video.snippet.publishedAt,
				viewCount: parseInt(video.statistics.viewCount) || 0
			};

			// Sauvegarder en cache
			try {
				fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));
			} catch (e) {
				console.log(`Erreur sauvegarde cache pour ${videoId}: ${e.message}`);
			}

			return metadata;
		}

		return { publishedAt: null, viewCount: 0 };
	} catch (e) {
		console.log(`Erreur récupération métadonnées pour ${videoId}: ${e.message}`);
		return { publishedAt: null, viewCount: 0 };
	}
}

/**
 * Récupérer la dernière vidéo d'un YouTuber via l'API YouTube
 */
async function getLatestVideo(youtuberName) {
	try {
		const channelId = CHANNEL_IDS[youtuberName];

		if (!channelId) {
			console.log(`Channel ID non trouvé pour ${youtuberName}`);
			return null;
		}

		console.log(`Récupération vidéos pour ${youtuberName} (${channelId})...`);

		// Récupérer la dernière vidéo du channel
		const searchUrl = `https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=${channelId}&maxResults=1&order=date&type=video&key=${YOUTUBE_API_KEY}`;
		const searchData = await makeRequest(searchUrl);

		if (!searchData.items || searchData.items.length === 0) {
			console.log(`Aucune vidéo trouvée pour ${youtuberName}`);
			return null;
		}

		const video = searchData.items[0];
		const videoId = video.id.videoId;

		// Récupérer les métadonnées détaillées
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

			if (video && video.publishedAt && isTodayUS(video.publishedAt)) {
				todayVideos.push(video);
				console.log(`✓ ${youtuber}: vidéo du jour trouvée - "${video.title}"`);
			} else {
				console.log(`✗ ${youtuber}: pas de vidéo du jour`);
			}

			// Délai entre les requêtes pour respecter les limites de l'API
			if (i < YOUTUBERS.length - 1) {
				await new Promise(resolve => setTimeout(resolve, REQUEST_DELAY));
			}

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

	console.log(`Création de la grille avec ${videos.length} vidéos...`);

	// Calculer les dimensions de la grille
	const cols = Math.ceil(Math.sqrt(videos.length));
	const rows = Math.ceil(videos.length / cols);

	// Dimensions des thumbnails
	const thumbnailSize = 320;
	const padding = 10;
	const titleHeight = 40;

	// Dimensions du canvas
	const canvasWidth = cols * (thumbnailSize + padding) + padding;
	const canvasHeight = rows * (thumbnailSize + titleHeight + padding) + padding;

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

		const x = col * (thumbnailSize + padding) + padding;
		const y = row * (thumbnailSize + titleHeight + padding) + padding;

		try {
			// Charger l'image
			const img = await getCachedImage(video.videoId, video.thumbnailUrl);

			// Dessiner le thumbnail
			ctx.drawImage(img, x, y, thumbnailSize, thumbnailSize);

			// Dessiner le titre (tronqué)
			ctx.fillStyle = '#000000';
			ctx.font = 'bold 14px Arial';
			const title = video.title.length > 40 ? video.title.substring(0, 40) + '...' : video.title;
			ctx.fillText(title, x, y + thumbnailSize + 20);

			// Dessiner le nom du channel et les vues
			ctx.fillStyle = '#666666';
			ctx.font = '12px Arial';
			const views = video.viewCount ? `${video.viewCount.toLocaleString()} vues` : 'Vues inconnues';
			ctx.fillText(`${video.channel} • ${views}`, x, y + thumbnailSize + 35);

			console.log(`✓ Thumbnail ${i + 1}/${videos.length} dessiné`);

		} catch (e) {
			console.log(`Erreur chargement image pour ${video.videoId}: ${e.message}`);

			// Dessiner un rectangle gris en cas d'erreur
			ctx.fillStyle = '#cccccc';
			ctx.fillRect(x, y, thumbnailSize, thumbnailSize);
			ctx.fillStyle = '#000000';
			ctx.font = '14px Arial';
			ctx.fillText('Erreur chargement', x, y + thumbnailSize / 2);
		}
	}

	// Ajouter un titre en haut de l'image
	ctx.fillStyle = '#000000';
	ctx.font = 'bold 24px Arial';
	const title = `Vidéos Crypto du ${new Date().toLocaleDateString('fr-FR', { timeZone: 'America/New_York' })} (${videos.length} vidéos)`;
	const titleWidth = ctx.measureText(title).width;
	ctx.fillText(title, (canvasWidth - titleWidth) / 2, 30);

	// Sauvegarder l'image
	const timestamp = Date.now();
	const outputPath = path.join(COMPOSITE_DIR, `daily_grid_${timestamp}.png`);

	const buffer = canvas.toBuffer('image/png');
	fs.writeFileSync(outputPath, buffer);

	console.log(`Grille sauvegardée: ${outputPath}`);
	return outputPath;
}

/**
 * Fonction principale
 */
async function main() {
	try {
		console.log("=== YouTube Daily Grid Generator (API Version) ===");
		console.log(`Date/heure actuelle (US): ${new Date().toLocaleString("en-US", { timeZone: "America/New_York" })}`);

		if (YOUTUBE_API_KEY === 'VOTRE_CLE_API_ICI') {
			console.log("⚠️  ATTENTION: Vous devez configurer votre clé API YouTube dans la variable d'environnement YOUTUBE_API_KEY");
			console.log("   Exemple: export YOUTUBE_API_KEY='votre_cle_api'");
			console.log("   Ou modifiez directement la variable YOUTUBE_API_KEY dans le script");
			return;
		}

		// Récupérer les vidéos du jour
		const todayVideos = await getTodayVideos();

		if (todayVideos.length === 0) {
			console.log("Aucune vidéo publiée aujourd'hui trouvée.");
			return;
		}

		console.log(`\n${todayVideos.length} vidéos du jour trouvées:`);
		todayVideos.forEach(video => {
			console.log(`- ${video.channel}: ${video.title} (${video.viewCount.toLocaleString()} vues)`);
		});

		// Créer la grille
		const gridPath = await createImageGrid(todayVideos);

		if (gridPath) {
			console.log(`\n✅ Grille créée avec succès: ${gridPath}`);
		} else {
			console.log("\n❌ Erreur lors de la création de la grille");
		}

	} catch (e) {
		console.error("Erreur dans le script principal:", e);
	}
}

// Exécuter le script
if (require.main === module) {
	main();
}

module.exports = {
	getTodayVideos,
	createImageGrid,
	isTodayUS,
	getLatestVideo
};

