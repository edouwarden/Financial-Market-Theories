const fs = require('fs');
const path = require('path');
const SAMPLE_MENTIONS_FILE = path.join(__dirname, '../data/sample/mentions.json');
const SAMPLE_ITEMS_FILE = path.join(__dirname, '../data/sample/items.json');
const STATE_DIR = path.join(__dirname, '../results/state');
const MENTIONS_FILE = path.join(STATE_DIR, 'mentions.json');
const ITEMS_FILE = path.join(STATE_DIR, 'items.json');
const TRADE_FILE = path.join(__dirname, '../results/trade.json');
const ALERTS_FILE = path.join(__dirname, '../results/alerts.jsonl');

/**
 * Alerts are written to a local JSONL file instead of being pushed to a chat
 * service. This keeps the collector self-contained and makes the alert history
 * part of the research artifact.
 */
function appendAlert(level, message) {
	const line = JSON.stringify({
		ts: new Date().toISOString(),
		level,
		message: String(message).slice(0, 2000),
	});
	fs.mkdirSync(path.dirname(ALERTS_FILE), { recursive: true });
	fs.appendFileSync(ALERTS_FILE, `${line}\n`);
	console.log(`[${level}] ${String(message).slice(0, 300)}`);
}



// Socket connection is now handled by connectSocket() which supports automatic reconnection
const SOCKET_URL = 'wss://pumpportal.fun/api/data';
let socket;
let ended = false;
let tried = 0;

function connectSocket() {
	socket = new WebSocket(SOCKET_URL);

	socket.addEventListener('open', async () => {
		console.log('Connected to server');
		try {
			await socket.send(JSON.stringify({ method: 'subscribeNewToken' }));
			await socket.send(JSON.stringify({
				method: 'subscribeAccountTrade',
				keys: process.env.PUMPPORTAL_ACCOUNT_KEYS ? process.env.PUMPPORTAL_ACCOUNT_KEYS.split(',') : [],
			}));
			tried = 0;
		} catch (err) {
			
		}
	});

	// message handler (moved from original declaration)
	socket.addEventListener('message', async (event) => {
		try {
			const data = JSON.parse(event.data);
			if (data.txType === 'create') {
				if (!data.uri) return;
				const resp = await Bun.fetch(data.uri);
				if (!resp.ok) return;
				const token = await resp.json();
				await processToken(token);
			} else {
				console.log('Account trade:', data);
				await Bun.write(TRADE_FILE, JSON.stringify(data, null, 2));
			}
		} catch (error) {
			console.error('Error:', error);
			fs.mkdirSync(path.join(__dirname, '../results'), { recursive: true });
			fs.writeFileSync(path.join(__dirname, '../results/error.log'), JSON.stringify({ ts: new Date().toISOString(), message: error.message }, null, 2));
		}
	});

	// error handler
	socket.addEventListener('error', async (event) => {
		appendAlert('error', `socket error: ${event?.message ?? 'unknown'}`);
		if (tried < 5) {
			await Bun.sleep(1000 * 60 * 2);
			connectSocket();
		}
		tried++;
	});

	// close handler – try to reconnect automatically
	socket.addEventListener('close', () => {
		if (!ended) {
			console.log('Socket closed. Reconnecting in 10 second…');
			setTimeout(connectSocket, 10000);
		}
	});
}

const MENTIONS_WINDOW_MS = 20 * 60 * 1000;

function readState(preferredFile, sampleFile, fallback) {
	const file = fs.existsSync(preferredFile) ? preferredFile : sampleFile;
	if (!fs.existsSync(file)) return fallback;
	try {
		return JSON.parse(fs.readFileSync(file, 'utf8'));
	} catch (error) {
		console.error(`Could not read ${file}: ${error.message}`);
		return fallback;
	}
}

const mentions = readState(MENTIONS_FILE, SAMPLE_MENTIONS_FILE, [])
	.filter((mention) => mention && Array.isArray(mention.keywords) && Array.isArray(mention.timestamps));

const items = new Map(
	readState(ITEMS_FILE, SAMPLE_ITEMS_FILE, [])
		.filter((entry) => Array.isArray(entry) && entry.length === 2),
);

function extractKeywords(text) {
	if (!text) return [];
	const stopwords = [
		// Anglais
		"a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
		"can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
		"haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
		"isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
		"out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
		"there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've",
		"and",
		"were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",

		"test", "coin", "token", "tokens"
	];
	if (text == "The only platform where you can launch, manage, and grow your token—all from one unified interface.") return [];
	if (text == " - Launched with unbeatable speed on launchblitz.ai") return [];
	if (text == "nova.trade") return [];
	if (text == "Deployed using https://j7tracker.com/") return [];
	return [...new Set(
		text
			.toLowerCase()
			.replace(/[^a-z0-9\s]/g, " ")
			.split(/\s+/)
			.filter(w => !stopwords.includes(w) && w.length > 1)
	)];
}


async function upsertMention({ keywords, twitterLink, websiteLink }) {
	const now = Date.now();

	// helper to decide if two mentions are related
	const overlapCount = (a, b) => a.filter(x => b.includes(x)).length;
	const isSimilar = (m) => {
		if (twitterLink && m.twitterLink && twitterLink === m.twitterLink) return true;
		if (websiteLink && m.websiteLink && websiteLink === m.websiteLink) return true;
		const overlap = overlapCount(keywords, m.keywords);
		const minLen = Math.min(keywords.length, m.keywords.length);
		if (minLen < 3) {
			return overlap >= 2; // all keywords must match for very small sets
		}
		return overlap >= 3;
	};

	let mention = mentions.find(isSimilar);
	if (!mention) {
		mention = {
			keywords: [...new Set(keywords)],
			twitterLink,
			websiteLink,
			timestamps: [],
			lastAlert: 0,
			fastAlert: false,
			importantAlert: false,
			groupAlert: false
		};
		mentions.push(mention);
	} else {
		// merge keywords / links
		mention.keywords.push(...keywords);
		// ensure uniqueness and cap size to prevent infinite growth
		mention.keywords = [...new Set(mention.keywords)].slice(0, 100);
		if (!mention.twitterLink) mention.twitterLink = twitterLink;
		if (!mention.websiteLink) mention.websiteLink = websiteLink;
	}

	// record occurrence
	mention.timestamps.push(now);
	// purge old
	mention.timestamps = mention.timestamps.filter(ts => now - ts < MENTIONS_WINDOW_MS);

	// trigger alert
	if (mention.timestamps.length >= 5) {
		let dest = null;
		if (!mention.fastAlert && mention.timestamps.length >= 10) {
			dest = 'fast';
			mention.fastAlert = true;
		} else if (!mention.groupAlert && mention.timestamps.length >= 30) {
			dest = 'group';
			mention.lastAlert = now;
			mention.groupAlert = true;
		}else if (!mention.importantAlert && mention.timestamps.length >= 40) {
			dest = 'important';
			mention.importantAlert = true;
		}
		if (dest) {
			appendAlert(dest, `Group alert: ${mention.keywords.join(', ')} — ${mention.timestamps.length} mentions in the last ${MENTIONS_WINDOW_MS / 60000} minutes. ${mention.description ? `Description: ${mention.description.slice(0, 200)}` : ''} ${mention.twitterLink ? `Twitter: ${mention.twitterLink}` : ''} ${mention.websiteLink ? `Website: ${mention.websiteLink}` : ''}`);
		}
	}
}
async function upsertItem(key, label, description = null, twitter = null, website = null) {
	if (!key) return;
	const now = Date.now();
	let record = items.get(key);
	if (!record) {
		record = { label, description, twitter, website, timestamps: [], lastAlert: 0, fastAlert: false, importantAlert: false, tokenAlert: false };
		items.set(key, record);
	}

	if (description && !record.description)
			record.description = description;
	
	if (twitter && !record.twitter) record.twitter = twitter;
	if (website && !record.website) record.website = website;

	// record occurrence
	record.timestamps.push(now);
	// purge old
	record.timestamps = record.timestamps.filter(ts => now - ts < MENTIONS_WINDOW_MS);

	const count = record.timestamps.length;
	const threshold = {
		fast: label === 'Keyword' ? 15 : label === 'Twitter' ? 10 : 7,
		token: label === 'Keyword' ? 30 : label === 'Twitter' ? 35 : 15,
		important: label === 'Keyword' ? 70 : label === 'Twitter' ? 50 : 25,
	};

	let dest = null;
	if (!record.fastAlert && count >= threshold.fast) {
		dest = 'fast';
		record.fastAlert = true;
	} else if (!record.tokenAlert && count >= threshold.token) {
		dest = 'token';
		record.lastAlert = now;
		record.tokenAlert = true;
	} else if (!record.importantAlert && count >= threshold.important) {
		dest = 'important';
		record.importantAlert = true;
	}
	if (dest) {
		appendAlert(dest, `Token alert: ${label} ${key} — ${count} mentions in the last ${MENTIONS_WINDOW_MS / 60000} minutes. ${record.description ? `Description: ${record.description.slice(0, 200)}` : ''} ${record.twitter ? `Twitter: ${record.twitter}` : ''} ${record.website ? `Website: ${record.website}` : ''}`);
	}

}


async function processToken(token) {
	let description = token?.description;
	if (description == "test"
		|| description == "The only platform where you can launch, manage, and grow your token—all from one unified interface."
		|| description == " - Launched with unbeatable speed on launchblitz.ai"
		|| description == "nova.trade"
		|| description == "Deployed using https://j7tracker.com/")
		description = null;
	const keywords = [
		...extractKeywords(token.name),
		...extractKeywords(description)
	];
	let website = token?.website;
	if (website && (website.includes("launchblitz.ai") || website.includes("axiom.trade")|| website.includes("pump.fun") || website.includes('padre.gg') || website.includes('j7tracker.com') || website.includes('nova.trade') || website.includes('localhost:'))) website = null;
	const data = {
		keywords,
		twitterLink: token?.twitter,
		websiteLink: website
	};
	await upsertMention(data);
	for (const keyword of keywords) {
		await upsertItem(keyword, "Keyword", description, token?.twitter, website);
	}
	if (token?.twitter) await upsertItem(token.twitter, "Twitter");
	if (website && website.includes('https://x.com')) await upsertItem(website, "Twitter");
	else if (website) await upsertItem(website, "Website");
}


function summarise() {
	const now = Date.now();
	for (let i = mentions.length - 1; i >= 0; i--) {
		const mention = mentions[i];
		mention.timestamps = mention.timestamps.filter((ts) => now - ts < MENTIONS_WINDOW_MS);
		if (mention.timestamps.length === 0) mentions.splice(i, 1);
	}
	for (const [key, record] of items) {
		record.timestamps = record.timestamps.filter((ts) => now - ts < MENTIONS_WINDOW_MS);
		if (record.timestamps.length === 0) items.delete(key);
	}

	const topGroups = mentions
		.filter((mention) => mention.timestamps.length > 2)
		.map((mention) => ({
			keywords: [...new Set(mention.keywords)].join(', '),
			count: mention.timestamps.length,
			twitter: mention.twitterLink ?? null,
			website: mention.websiteLink ?? null,
		}))
		.sort((a, b) => b.count - a.count)
		.slice(0, 10);

	const topItems = Array.from(items.entries())
		.filter(([, record]) => record.timestamps.length > 2)
		.sort(([, a], [, b]) => b.timestamps.length - a.timestamps.length)
		.slice(0, 20)
		.map(([key, record]) => ({ key, label: record.label, count: record.timestamps.length }));

	return {
		ts: new Date().toISOString(),
		activeMentions: mentions.length,
		activeItems: items.size,
		topGroups,
		topItems,
	};
}

setInterval(() => {
	console.clear();
	console.log(JSON.stringify(summarise(), null, 2));
}, 5000);

process.on('SIGINT', async () => {
	console.log('Shutting down...');
	ended = true;
	socket?.close();

	fs.mkdirSync(path.dirname(MENTIONS_FILE), { recursive: true });
	fs.writeFileSync(MENTIONS_FILE, JSON.stringify(mentions, null, 2));
	fs.writeFileSync(ITEMS_FILE, JSON.stringify(Array.from(items.entries()), null, 2));
	process.exit(0);
});

if (require.main === module) {
	connectSocket();
}

module.exports = {
	extractKeywords,
	upsertMention,
	upsertItem,
	processToken,
	summarise,
};