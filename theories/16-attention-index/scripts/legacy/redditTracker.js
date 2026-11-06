import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'reddit-tracker.json');

export async function redditTracker() {
	const url = 'https://reddit-stock-and-crypto-tracker.p.rapidapi.com/all-crypto/page/1';
	const options = {
		method: 'GET',
		headers: {
			'x-rapidapi-key': process.env.RAPIDAPI_KEY,
			'x-rapidapi-host': 'reddit-stock-and-crypto-tracker.p.rapidapi.com'
		}
	};

	const response = await fetch(url, options);
	const result = await response.json();
	const coins = result.results.slice(0, 20);

	const report = {
		title: 'Reddit Tracker',
		description: 'Latest Reddit posts about crypto',
		coins: coins.map(coin => ({
			...coin,
			rankDelta: coin.rank_24h_ago - coin.rank,
			mentionsDelta: coin.mentions_24h_ago - coin.mentions,
			summary: `🏆Rank 24h: ${coin.rank_24h_ago}${(coin.rank_24h_ago > coin.rank ? '📈+' : '📉')}${coin.rank_24h_ago - coin.rank}\n💬Mention: ${coin.mentions}${coin.mentions_24h_ago > coin.mentions ? '📈+' : '📉'}${coin.mentions_24h_ago - coin.mentions}\n🟢upvote: ${coin.upvotes}`
		})),
		source: 'Data from Reddit Stock and Crypto Tracker via RapidAPI',
		generatedAt: new Date().toISOString()
	};

	await mkdir(RESULTS_DIR, { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));

	return report;
}

async function main() {
	const report = await redditTracker();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
