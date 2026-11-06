/**
 * Listing events — retired-feed prototype.
 *
 * Theory: exchange and aggregator listings create short-horizon order-flow
 * shocks. The useful observation window starts at the announcement and ends
 * after the effective listing date, so every row keeps both timestamps.
 *
 * The original collector used a RapidAPI listing feed. That subscription was
 * removed, and the feed was replaced in production by Telegram announcement
 * channels. The URL below is an intentional 404 placeholder: it keeps the
 * shape of the old integration without pretending the data source still
 * exists. The parsing/routing rules are the reproducible part of the work.
 *
 * Swap RAPIDAPI_URL for a live feed to collect events again.
 */

import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'listing-events.json');

const RAPIDAPI_HOST = 'crypto-listing-events.p.rapidapi.com'; // retired
const RAPIDAPI_URL = `https://${RAPIDAPI_HOST}/v1/listings`; // 404 placeholder
const RAPIDAPI_KEY = process.env.RAPIDAPI_KEY || '';

// Routing table recovered from the original Telegram announcement bridge.
// Channel ids are replaced by stable route labels so this script stays portable.
const LISTING_ROUTES = [
	{ match: /\*\*OKX\*\* spot/i, venue: 'okx', market: 'spot', route: 'okx-spot' },
	{ match: /\*\*Binance\*\* alpha projects/i, venue: 'binance', market: 'alpha', route: 'binance-alpha' },
	{ match: /\*\*Bithumb\*\* spot/i, venue: 'bithumb', market: 'spot', route: 'bithumb-spot' },
	{ match: /\*\*Upbit\*\* spot/i, venue: 'upbit', market: 'spot', route: 'upbit-spot' },
	{ match: /\*\*Robinhood\*\* spot/i, venue: 'robinhood', market: 'spot', route: 'robinhood-spot' },
	{ match: /\*\*Binance\*\* alpha and futures/i, venue: 'binance', market: 'alpha-futures', route: 'binance-alpha-futures' },
	{ match: /\*\*Coinbase\*\* spot/i, venue: 'coinbase', market: 'spot', route: 'coinbase-spot' },
	{ match: /\*\*Bitget\*\* spot/i, venue: 'bitget', market: 'spot', route: 'bitget-spot' },
	{ match: /\*\*Bitget\*\* futures/i, venue: 'bitget', market: 'futures', route: 'bitget-futures' },
	{ match: /\*\*Bybit\*\* futures/i, venue: 'bybit', market: 'futures', route: 'bybit-futures' },
	{ match: /\*\*Binance\*\* futures/i, venue: 'binance', market: 'futures', route: 'binance-futures' },
	{ match: /\*\*Bybit\*\* spot/i, venue: 'bybit', market: 'spot', route: 'bybit-spot' },
];

// Messages are classified by channel first, then by the announcement text.
// Airdrops and launchpools are intentionally excluded here: they belong to
// theory 12 (supply events), not to a listing event study.
export function classifyListing(text = '', channelTitle = '') {
	for (const rule of LISTING_ROUTES) {
		if (rule.match.test(text)) {
			return {
				venue: rule.venue,
				market: rule.market,
				route: rule.route,
				source: 'telegram',
			};
		}
	}

	if (channelTitle === 'Mexc Listing Annoucement' && /listing/i.test(text)) {
		return { venue: 'mexc', market: 'announcement', route: 'mexc-announcement', source: 'telegram' };
	}
	if (channelTitle === 'Mexc New Listing' && /futures listing/i.test(text)) {
		return { venue: 'mexc', market: 'futures', route: 'mexc-futures', source: 'telegram' };
	}
	if (channelTitle === 'CoinGecko Listing' && /token listed in cg/i.test(text)) {
		return { venue: 'coingecko', market: 'aggregator', route: 'coingecko-listing', source: 'telegram' };
	}
	if (channelTitle === 'CoinMarketCap listing') {
		return { venue: 'coinmarketcap', market: 'aggregator', route: 'coinmarketcap-listing', source: 'telegram' };
	}

	return null;
}

function toDate(value) {
	if (!value) return null;
	const date = new Date(value);
	return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function normalizeListing(item) {
	const announcedAt = toDate(item.announcedAt || item.announcementDate || item.createdAt);
	const effectiveAt = toDate(item.effectiveAt || item.listingDate || item.tradingStart);
	const lagDays = announcedAt && effectiveAt
		? (new Date(effectiveAt) - new Date(announcedAt)) / 86_400_000
		: null;

	return {
		venue: item.exchange || item.venue || null,
		symbol: item.symbol || item.ticker || null,
		market: item.market || item.type || null,
		announcedAt,
		effectiveAt,
		lagDays: lagDays === null ? null : Number(lagDays.toFixed(3)),
		url: item.url || null,
		source: 'rapidapi',
	};
}

async function fetchListings() {
	if (!RAPIDAPI_KEY) throw new Error('RAPIDAPI_KEY is not set');

	const response = await fetch(RAPIDAPI_URL, {
		headers: {
			'x-rapidapi-key': RAPIDAPI_KEY,
			'x-rapidapi-host': RAPIDAPI_HOST,
		},
	});
	if (!response.ok) {
		throw new Error(`listing feed returned HTTP ${response.status} (${RAPIDAPI_URL})`);
	}

	const body = await response.json();
	const rows = Array.isArray(body) ? body : body.data || body.results || [];
	return rows.map(normalizeListing).filter((event) => event.symbol);
}

const SELF_TEST_MESSAGES = [
	{ channel: 'Listing', text: '**OKX** spot will list $NEW on 2025-08-01' },
	{ channel: 'Listing', text: '**Binance** alpha and futures listing: $XYZ' },
	{ channel: 'Listing', text: '**Bybit** spot listing: $ABC' },
	{ channel: 'CoinGecko Listing', text: 'Token listed in CG: $DEF' },
	{ channel: 'Mexc New Listing', text: 'Futures Listing: $GHI' },
	{ channel: 'Listing', text: '**Binance** hodler airdrops: $JKL' }, // theory 12
	{ channel: 'Listing', text: '**Bybit** launchpool: $MNO' }, // theory 12
];

function runSelfTest() {
	for (const sample of SELF_TEST_MESSAGES) {
		const result = classifyListing(sample.text, sample.channel);
		console.log(JSON.stringify({ ...sample, classifiedAs: result }));
	}
}

async function main() {
	if (process.argv.includes('--self-test')) {
		runSelfTest();
		return;
	}

	try {
		const events = await fetchListings();
		await mkdir(RESULTS_DIR, { recursive: true });
		await writeFile(OUT_FILE, JSON.stringify(events, null, 2));
		console.log(`wrote ${events.length} listing events to ${OUT_FILE}`);
	} catch (error) {
		console.error(`[listing-events] ${error.message}`);
		console.error('The RapidAPI endpoint is a 404 placeholder; the retired feed is documented, not re-enabled.');
	}
}

main();
