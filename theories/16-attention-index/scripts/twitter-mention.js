import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../results');
const RAW_FILE = join(RESULTS_DIR, 'twitter-mention.json');
const TRENDING_FILE = join(RESULTS_DIR, 'twitter-mention-trending.json');

// Market cap categories
const MARKET_CAP_CATEGORIES = {
	LARGE: { min: 500_000_000, label: '🔷 Large Cap (>$500M)', color: 0x0099FF },
	MID: { min: 100_000_000, max: 500_000_000, label: '🔶 Mid Cap ($100M-$500M)', color: 0x00BFFF },//light blue
	SMALL: { min: 10_000_000, max: 100_000_000, label: '💠 Small Cap ($10M-$100M)', color: 0x00FF00 },//green
	MICRO: { max: 10_000_000, label: '💎 Micro Cap (<$10M)', color: 0x9400D3 }//purple
};

const COINS_PER_CATEGORY = 5; // Number of coins to show per category

const sleep = (ms) => new Promise(resolveSleep => setTimeout(resolveSleep, ms));

// Format number with appropriate suffix (K, M, B)
const formatNumber = (num) => {
	if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(2) + 'B';
	if (num >= 1_000_000) return (num / 1_000_000).toFixed(2) + 'M';
	if (num >= 1_000) return (num / 1_000).toFixed(2) + 'K';
	return num.toFixed(2);
};

// Categorize tokens by market cap
const categorizeTokens = (tokens) => {
	const categories = {
		LARGE: [],
		MID: [],
		SMALL: [],
		MICRO: []
	};

	tokens.forEach(token => {
		const marketCap = parseFloat(token.market_cap);
		if (marketCap >= MARKET_CAP_CATEGORIES.LARGE.min) {
			categories.LARGE.push(token);
		} else if (marketCap >= MARKET_CAP_CATEGORIES.MID.min) {
			categories.MID.push(token);
		} else if (marketCap >= MARKET_CAP_CATEGORIES.SMALL.min) {
			categories.SMALL.push(token);
		} else {
			categories.MICRO.push(token);
		}
	});

	// Sort each category by attentionPercentage and limit the number of coins
	Object.keys(categories).forEach(category => {
		categories[category].sort((a, b) => b.attentionPercentage - a.attentionPercentage);
		categories[category] = categories[category].slice(0, COINS_PER_CATEGORY);
	});

	return categories;
};

const serializeToken = (token) => ({
	...token,
	marketCap: parseFloat(token.market_cap),
	marketCapLabel: `$${formatNumber(parseFloat(token.market_cap))} MC`,
	summary:
		`🕐 24h Mentions: ${token.mentions24h} | 🧠 Mindshare: ${token.mindshare}\n` +
		`🍰 Influence: ${token.influencePercentage}% ${token.influenceChange24h > 0 ? '🔺' : token.influenceChange24h < 0 ? '🔻' : ''} ${token.influenceChange24h} | ` +
		`👀 Attention: ${token.attentionScore} ● ${token.attentionPercentage}% ${token.attentionDelta24h > 0 ? '🔺' : token.attentionDelta24h < 0 ? '🔻' : ''}\n` +
		`🎯 Score: ${token.checkrScore} ● ${token.checkrScorePercentage}% ● local ${token.checkrScorePercentile}%`
});

// Build a structured category for trending coins
const createTrendingCategory = (tokens, categoryName) => {
	const categoryInfo = MARKET_CAP_CATEGORIES[categoryName];
	return {
		category: categoryName,
		label: categoryInfo.label,
		color: categoryInfo.color,
		tokens: tokens.map(serializeToken)
	};
};



// Helper: fetch and return json, throwing on non-200
const fetchJson = async (url, options = {}) => {
	const res = await fetch(url, options);
	if (!res.ok) throw new Error(`Failed to fetch: ${url} → ${res.status}`);
	const { data } = await res.json();
	if (!data) throw new Error('No data field in response');
	return data;
};

// Fetch GeckoTerminal market-cap data (max 30 tokens)
export const addMarketCap = async (tokens, network = 'base') => {
	if (!tokens?.length) throw new Error('Token addresses array is required');
	if (tokens.length > 30) throw new Error('Maximum 30 token addresses allowed per request');

	// Extract token addresses from token objects
	const addressesString = tokens.map(t => t.gt_token_address).join(',');
	const url = `https://api.geckoterminal.com/api/v2/simple/networks/${network}/token_price/${addressesString}?include_market_cap=true`;

	const { attributes } = await fetchJson(url, {
		headers: {
			Accept: 'application/json',
			'User-Agent': 'Mozilla/5.0 (compatible; CryptoBot/1.0)'
		}
	});

	// Transform the data into a more usable format
	return {
		token_prices: attributes.token_prices || {},
		market_caps: attributes.market_cap_usd || {},
		timestamp: new Date().toISOString()
	};
};

const copyProps = (src, dest, props) => props.forEach(p => src[p] !== undefined && (dest[p] = src[p]));
const mergeData = (data, items, props) => {
	if (Array.isArray(items)) {
		items.forEach(item => {
			const key = item.symbol ?? Object.keys(item)[0];
			const target = data[key];
			if (!target) return;
			copyProps(item, target, props);
		});
	} else {
		// Handle object format where keys are symbols
		Object.entries(items).forEach(([symbol, itemData]) => {
			const target = data[symbol];
			if (!target) return;
			copyProps(itemData, target, props);
		});
	}
};

// Main entry: fetch tokens, enrich with market-cap & 24h mention counts
export async function twitterMention() {
	try {
		// 1. Fetch token list
		let data = await fetchJson('https://checkr.social/api/tokens?source=farcaster');

		// 2. Index by symbol for easy lookups
		data = data.reduce((acc, item) => ({ ...acc, [item.symbol]: item }), {});

		// 3. Split by chain
		const tokens = Object.values(data);
		const base = tokens.filter(t => t.gt_chain === 'base');
		const others = tokens.filter(t => t.gt_chain !== 'base');

		// 4. Batch fetch market-caps for Base chain (30-per-call limit)
		for (let i = 0; i < base.length; i += 30) {
			const batch = base.slice(i, i + 30);
			const { market_caps } = await addMarketCap(batch);
			batch.forEach(token => (token.market_cap = market_caps[token.gt_token_address] || 0));
			await sleep(250);
		}

		// 5. Fetch market-caps for other chains one-by-one (rarer)
		for (const token of others) {
			const { market_caps } = await addMarketCap([token], token.gt_chain);
			token.market_cap = market_caps[token.gt_token_address] || 0;
			await sleep(250);
		}

		// 6. Fetch additional metrics and merge
		mergeData(data, await fetchJson('https://checkr.social/api/token24hCasts?source=farcaster'), ['mentions24h']);
		mergeData(data, await fetchJson('https://checkr.social/api/influence-percentages?source=farcaster'), ['influencePercentage', 'influenceChange24h', 'influenceDelta24h']);
		mergeData(data, await fetchJson('https://checkr.social/api/attention-metrics?source=farcaster'), [
			'checkrScore',
			'attentionScore',
			'attentionPercentage',
			'pulsePercentage',
			'checkrScorePercentage',
			'checkrScorePercentile',
			'previousAttentionPercentage',
			'attentionDelta24h'
		]);

		await mkdir(RESULTS_DIR, { recursive: true });

		// Save raw data to file
		await writeFile(RAW_FILE, JSON.stringify(data, null, 2));

		// 7. Build trending coin categories
		const tokenCategories = categorizeTokens(Object.values(data));
		const categories = Object.entries(tokenCategories)
			.filter(([, tokens]) => tokens.length > 0)
			.map(([categoryName, tokens]) => createTrendingCategory(tokens, categoryName));

		const report = {
			title: 'Trending coins by market cap',
			categories,
			tokenCount: Object.keys(data).length,
			rawDataPath: RAW_FILE,
			source: 'Data from Checkr Social and GeckoTerminal',
			generatedAt: new Date().toISOString()
		};

		await writeFile(TRENDING_FILE, JSON.stringify(report, null, 2));

		return report;
	} catch (error) {
		console.error('Error in twitterMention:', error);
		throw error;
	}
}

async function main() {
	const report = await twitterMention();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
