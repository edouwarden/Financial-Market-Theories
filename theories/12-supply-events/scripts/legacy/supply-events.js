/**
 * Supply events — retired-feed prototype.
 *
 * Theory: token unlocks, airdrops and launchpool distributions create
 * predictable supply pressure when the recipient base is likely to sell.
 * The event study needs the event date, the amount distributed, circulating
 * supply at the time, and recipient composition — not just a headline date.
 *
 * The original collector used a RapidAPI supply-event feed. That subscription
 * was removed and replaced in production by Telegram announcement channels.
 * The URL below is an intentional 404 placeholder, so the integration shape
 * stays visible without pretending the feed still exists.
 *
 * Swap RAPIDAPI_URL for a live feed to collect events again.
 */

import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'supply-events.json');

const RAPIDAPI_HOST = 'token-supply-events.p.rapidapi.com'; // retired
const RAPIDAPI_URL = `https://${RAPIDAPI_HOST}/v1/unlocks`; // 404 placeholder
const RAPIDAPI_KEY = process.env.RAPIDAPI_KEY || '';

// Classification recovered from the original Telegram announcement bridge.
// Listing announcements stay in theory 07; only distribution events are kept here.
const SUPPLY_ROUTES = [
	{
		match: /\*\*Binance\*\* hodler airdrops/i,
		venue: 'binance',
		kind: 'airdrop',
		route: 'binance-hodler-airdrop',
	},
	{
		match: /\*\*Bybit\*\* launchpool/i,
		venue: 'bybit',
		kind: 'launchpool',
		route: 'bybit-launchpool',
	},
];

const GENERIC_SUPPLY_RULES = [
	{ match: /\bunlock(s|ed|ing)?\b/i, kind: 'unlock' },
	{ match: /\bairdrop(s|ped|ping)?\b/i, kind: 'airdrop' },
	{ match: /\blaunchpool\b/i, kind: 'launchpool' },
	{ match: /\bvesting\b/i, kind: 'vesting' },
	{ match: /\b(tge|token generation event)\b/i, kind: 'tge' },
];

export function classifySupplyEvent(text = '', channelTitle = '') {
	for (const rule of SUPPLY_ROUTES) {
		if (rule.match.test(text)) {
			return {
				venue: rule.venue,
				kind: rule.kind,
				route: rule.route,
				source: 'telegram',
			};
		}
	}

	for (const rule of GENERIC_SUPPLY_RULES) {
		if (rule.match.test(text)) {
			return {
				venue: null,
				kind: rule.kind,
				route: `generic-${rule.kind}`,
				source: channelTitle ? 'telegram' : 'text',
			};
		}
	}

	return null;
}

function toDate(value) {
	if (!value) return null;
	const date = new Date(value);
	return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function normalizeSupplyEvent(item) {
	const eventAt = toDate(item.eventAt || item.unlockAt || item.date || item.createdAt);
	const amount = Number(item.amount ?? item.unlockAmount ?? 0) || null;
	const circulatingSupply = Number(item.circulatingSupply ?? 0) || null;
	const supplyPressure = amount && circulatingSupply
		? amount / circulatingSupply
		: null;
	const daysUntil = eventAt
		? (new Date(eventAt) - Date.now()) / 86_400_000
		: null;

	return {
		venue: item.exchange || item.venue || null,
		symbol: item.symbol || item.ticker || null,
		kind: item.kind || item.type || null,
		eventAt,
		daysUntil: daysUntil === null ? null : Number(daysUntil.toFixed(2)),
		amount,
		circulatingSupply,
		supplyPressure: supplyPressure === null ? null : Number(supplyPressure.toFixed(6)),
		recipients: item.recipients || item.recipientComposition || null,
		url: item.url || null,
		source: 'rapidapi',
	};
}

async function fetchSupplyEvents() {
	if (!RAPIDAPI_KEY) throw new Error('RAPIDAPI_KEY is not set');

	const response = await fetch(RAPIDAPI_URL, {
		headers: {
			'x-rapidapi-key': RAPIDAPI_KEY,
			'x-rapidapi-host': RAPIDAPI_HOST,
		},
	});
	if (!response.ok) {
		throw new Error(`supply feed returned HTTP ${response.status} (${RAPIDAPI_URL})`);
	}

	const body = await response.json();
	const rows = Array.isArray(body) ? body : body.data || body.results || [];
	return rows.map(normalizeSupplyEvent).filter((event) => event.symbol);
}

const SELF_TEST_MESSAGES = [
	{ channel: 'Listing', text: '**Binance** hodler airdrops: $JKL — snapshot 2025-08-01' },
	{ channel: 'Listing', text: '**Bybit** launchpool: $MNO — farming starts 2025-08-03' },
	{ channel: 'Unlocks', text: '$PQR token unlock: 12,000,000 tokens on 2025-08-15' },
	{ channel: 'Unlocks', text: '$STU vesting cliff ends next week' },
	{ channel: 'Listing', text: '**OKX** spot will list $NEW' }, // theory 07
];

function runSelfTest() {
	for (const sample of SELF_TEST_MESSAGES) {
		const result = classifySupplyEvent(sample.text, sample.channel);
		console.log(JSON.stringify({ ...sample, classifiedAs: result }));
	}
}

async function main() {
	if (process.argv.includes('--self-test')) {
		runSelfTest();
		return;
	}

	try {
		const events = await fetchSupplyEvents();
		await mkdir(RESULTS_DIR, { recursive: true });
		await writeFile(OUT_FILE, JSON.stringify(events, null, 2));
		console.log(`wrote ${events.length} supply events to ${OUT_FILE}`);
	} catch (error) {
		console.error(`[supply-events] ${error.message}`);
		console.error('The RapidAPI endpoint is a 404 placeholder; the retired feed is documented, not re-enabled.');
	}
}

main();
