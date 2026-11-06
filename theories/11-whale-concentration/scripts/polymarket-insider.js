import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../results');
const OUT_FILE = join(RESULTS_DIR, 'polymarket-insider.json');

/**
 * Fetch recent large Polymarket positions and keep the subset that looks like
 * informed flow: price below 0.5, size above 2,000, positive PnL, and a trade
 * timestamp inside the last day.
 *
 * This is a screening heuristic, not a tested signal. It deliberately does not
 * publish wallet addresses or trader profile data.
 */
export async function polymarketInsider() {
	const response = await fetch('https://wallettrackapi-655880131780.us-central1.run.app/');
	if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);

	const payload = await response.json();
	if (payload.status !== 'success' || !Array.isArray(payload.data)) {
		throw new Error('Unexpected response shape from the Polymarket wallet feed');
	}

	const cutoff = Math.floor((Date.now() - 24 * 60 * 60 * 1000) / 1000);
	const screened = payload.data
		.filter((trade) => trade.price < 0.5 && trade.size > 2000 && trade.user_profit_loss > 0 && trade.timestamp > cutoff)
		.sort((a, b) => b.price - a.price)
		.slice(0, 25)
		.map((trade) => ({
			market: trade.title,
			slug: trade.slug,
			outcome: trade.outcome,
			side: trade.side,
			price: trade.price,
			size: trade.size,
			notional: Number((trade.price * trade.size).toFixed(2)),
			userProfitLoss: trade.user_profit_loss,
			marketVolume: trade.market_volume_traded,
			timestamp: new Date(trade.timestamp * 1000).toISOString(),
		}));

	const report = {
		generatedAt: new Date().toISOString(),
		cutoff: new Date(cutoff * 1000).toISOString(),
		candidateCount: screened.length,
		candidates: screened,
		caveats: [
			'This is a screen, not a validated insider signal.',
			'Wallet identity fields are intentionally dropped from the output.',
			'Forward returns and matched non-concentrated markets are not tested here.',
		],
	};

	await mkdir(RESULTS_DIR, { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));
	return report;
}

async function main() {
	const report = await polymarketInsider();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
