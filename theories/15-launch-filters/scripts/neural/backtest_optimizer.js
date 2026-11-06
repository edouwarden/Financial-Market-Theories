import { readFile, writeFile } from 'fs/promises';
import { glob } from 'glob';

const DATA_GLOB = 'data/new_*.csv';
const SUCCESS_GLOB = 'data/success_*.csv';
const RESULT_FILE = 'logs/optimizer_results.json';


function checkFilter(token, f) {
	const buys_5m = token.txns_5m.buys;
	const sells_5m = token.txns_5m.sells;
	const ratio_5m = sells_5m === 0 ? Infinity : buys_5m / sells_5m;
	const buys_24h = token.txns_24h.buys;
	const sells_24h = token.txns_24h.sells;
	const ratio_24h = sells_24h === 0 ? Infinity : buys_24h / sells_24h;
	const priceChange_5m = token.priceChange_5m;

	const liq = token.liquidity;
	const price = token.priceUsd;
	const marketCap = token.marketCap;
	const fdv = token.fdv;
	const pairCreatedAt = token.pairCreatedAt;
	const volume_24h = token.volume_24h;

	return (
		buys_5m >= f.buysMin && buys_5m <= f.buysMax &&
		sells_5m >= f.sellsMin && sells_5m <= f.sellsMax &&
		ratio_5m >= f.ratioMin && ratio_5m <= f.ratioMax &&
		buys_24h >= f.buysMin && buys_24h <= f.buysMax &&
		sells_24h >= f.sellsMin && sells_24h <= f.sellsMax &&
		ratio_24h >= f.ratioMin && ratio_24h <= f.ratioMax &&
		priceChange_5m >= f.priceChangeMin && priceChange_5m <= f.priceChangeMax &&
		liq >= f.liquidityMin && liq <= f.liquidityMax &&
		price >= f.priceMin && price <= f.priceMax &&
		marketCap >= f.marketCapMin && marketCap <= f.marketCapMax &&
		fdv >= f.fdvMin && fdv <= f.fdvMax &&
		pairCreatedAt >= f.pairCreatedAtMin && pairCreatedAt <= f.pairCreatedAtMax &&
		volume_24h >= f.volumeMin && volume_24h <= f.volumeMax
	);
}

function evaluateFilter(filter, tokens, success, targetMultiple) {
	let trades = 0;
	let wins = 0;

	for (const token of Object.values(tokens)) {
		// Skip tokens that don’t match the filter
		if (!checkFilter(token, filter)) continue;

		trades++;

		// Best multiplier achieved by this token
		let tokenBest = success[token.tokenAddress]?.multiplier || 0;

		if (tokenBest >= targetMultiple) 
			wins++; // count max one win per token
		
	}

	const winRate = trades === 0 ? 0 : wins / trades;
	return { filter, trades, wins, winRate };
}


class DataLoader {
	constructor() {
		this.historicalData = {};
		this.successData = {};
	}

	async load() {
		await this._loadHistorical();
		await this._loadSuccess();
	}

	async _loadHistorical() {
		const files = await glob(DATA_GLOB);
		for (const file of files) {
			const content = await readFile(file, 'utf8');
			const lines = content.split('\n').filter(l => l.trim());
			for (const line of lines) {
				try {
					const data = JSON.parse(line);
					if (!Array.isArray(data) || data.length === 0) continue;
					const pair = data[0];
					this.historicalData[pair.baseToken?.address] = {
						tokenAddress: pair.baseToken?.address,
						tokenName: pair.baseToken?.name,
						tokenSymbol: pair.baseToken?.symbol,
						priceUsd: parseFloat(pair.priceUsd) || 0,
						marketCap: parseFloat(pair.marketCap) || 0,
						fdv: parseFloat(pair.fdv) || 0,
						liquidity: parseFloat(pair.liquidity?.usd) || 0,
						volume_24h: parseFloat(pair.volume?.h24) || 0,
						txns_24h: {
							buys: parseInt(pair.txns?.h24?.buys) || 0,
							sells: parseInt(pair.txns?.h24?.sells) || 0
						},
						txns_5m: {
							buys: parseInt(pair.txns?.m5?.buys) || 0,
							sells: parseInt(pair.txns?.m5?.sells) || 0
						},
						priceChange_5m: parseFloat(pair.priceChange?.m5) || 0,
						pairCreatedAt: parseInt(pair.pairCreatedAt) || 0
					};
				} catch (_) {/* ignore bad lines */ }
			}
		}
	}

	async _loadSuccess() {
		const files = await glob(SUCCESS_GLOB);
		for (const file of files) {
			const content = await readFile(file, 'utf8');
			const lines = content.split('\n').filter(l => l.trim());
			for (const line of lines) {
				try {
					const [timestamp, tokenAddress, tokenName, multiplier] = line.split(',');
					if (!timestamp || !tokenAddress || !tokenName || !multiplier) continue;
					this.successData[tokenAddress] = {
								timestamp: new Date(timestamp).getTime(),
								multiplier: parseFloat(multiplier)
						};
					
				} catch (_) {/* ignore */ }
			}
		}
	}
}


async function main() {
	console.time('optimization');
	console.log('📥 Loading data…');
	const loader = new DataLoader();
	await loader.load();
	const tokens = loader.historicalData;
	const success = loader.successData;
	console.log(`✅ Loaded ${Object.keys(tokens).length} token snapshots and ${Object.keys(success).length} success records.`);

	// === Generate filters
	console.log('🛠️ Generating filter candidates…');
	const filters = generateFilters();
	console.log(`⚙️  Evaluating ${filters.length} filters…`);

	const evaluations = filters.map(f => evaluateFilter(f, tokens, success, 2));
	const evaluations2 = filters.map(f => evaluateFilter(f, tokens, success, 100));

	// === Build leaderboards
	const bestWinRate = evaluations
		.filter(e => e.trades >= 35 && e.winRate >= 0.9)
		.sort((a, b) => b.winRate - a.winRate || b.trades - a.trades)
		.slice(0, 20);

	const bestMultiple = evaluations2
		.filter(e => e.bestMultiplier >= 100 && e.wins >= 3 && e.winRate >= 0.01)
		.slice(0, 20);

	const bestRetention = evaluations
		.filter(e => e.winRate >= 0.6 && e.trades >= Object.keys(tokens).length * 0.2)
		.sort((a, b) => b.trades - a.trades)
		.slice(0, 20);

	const result = { generated: filters.length, bestWinRate, bestMultiple, bestRetention };
	await writeFile(RESULT_FILE, JSON.stringify(result, null, 2));
	console.log(`📄 Results written to ${RESULT_FILE}`);

	console.log('🏆 Leaderboards');
	const fmtPct = n => (n * 100).toFixed(1) + '%';
	const fmt = (e) => `Trades: ${e.trades}\tWins: ${e.wins}\tWR: ${fmtPct(e.winRate)}`;

	console.log('\n=== Best Win Rate');
	bestWinRate.forEach(e => console.log(fmt(e)));

	console.log('\n=== Best Multiplier');
	bestMultiple.forEach(e => console.log(fmt(e)));

	console.log('\n=== Best Retention');
	bestRetention.forEach(e => console.log(fmt(e)));

	console.timeEnd('optimization');
}

// Run
main().catch(err => {
	console.error('❌ Optimizer failed', err);
	process.exit(1);
});
