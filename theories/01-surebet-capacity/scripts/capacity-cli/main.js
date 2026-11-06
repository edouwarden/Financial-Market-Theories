#!/usr/bin/env bun
/**
 * Surebet capacity CLI.
 *
 * Two modes:
 *   --replay <orderbook_pair.json>  recompute the committed sample offline
 *   --live                          fetch the monitored venues and write a snapshot
 *
 * The walker expects incremental ask levels: each { price, size } is the next
 * slice of the book, not a cumulative total. Futuur's UI returns a stake curve
 * (stake -> average price), so FutuurClient converts it to incremental levels
 * before it reaches this file.
 *
 * Fees are opt-in because they are venue- and account-specific:
 *   --fee-bps 100
 */

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '../..');
const FutuurClient = require('./FutuurClient');
const PolymarketClient = require('./PolymarketClient');

const DEFAULTS = {
	feeBps: 0,
	minOrderSize: 1,
};

function parseArgs(argv) {
	const args = { _: [] };
	for (let i = 2; i < argv.length; i++) {
		const token = argv[i];
		if (!token.startsWith('--')) {
			args._.push(token);
			continue;
		}
		const [key, inline] = token.slice(2).split('=');
		if (inline !== undefined) {
			args[key] = inline;
		} else if (argv[i + 1] && !argv[i + 1].startsWith('--')) {
			args[key] = argv[++i];
		} else {
			args[key] = true;
		}
	}
	return args;
}

function round(value, digits = 2) {
	return Number(Number(value).toFixed(digits));
}

function loadJson(file) {
	return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeJson(file, value) {
	fs.mkdirSync(path.dirname(file), { recursive: true });
	fs.writeFileSync(file, JSON.stringify(value, null, 2));
}

function normaliseAsks(asks) {
	return (Array.isArray(asks) ? asks : [])
		.map(({ price, size }) => ({ price: Number(price), size: Number(size) }))
		.filter(({ price, size }) => Number.isFinite(price) && price > 0 && price <= 1 && Number.isFinite(size) && size > 0)
		.sort((a, b) => a.price - b.price);
}

function getLevelAtQuantity(asks, targetQuantity) {
	let cumulative = 0;
	let cost = 0;
	for (const { price, size } of asks) {
		if (cumulative + size >= targetQuantity) {
			const remaining = targetQuantity - cumulative;
			return { price, cost: cost + remaining * price };
		}
		cumulative += size;
		cost += size * price;
	}
	return null;
}

function withMinimumCosts(range, asksA, asksB) {
	const minA = getLevelAtQuantity(asksA, range.minQuantity);
	const minB = getLevelAtQuantity(asksB, range.minQuantity);
	if (!minA || !minB) return range;
	return {
		...range,
		minCostA: minA.cost,
		minCostB: minB.cost,
		minPriceA: minA.cost / range.minQuantity,
		minPriceB: minB.cost / range.minQuantity,
	};
}

function findQuantityRanges(asksA, asksB, options = {}) {
	const feeBps = Number(options.feeBps ?? DEFAULTS.feeBps);
	const asksA2 = normaliseAsks(asksA);
	const asksB2 = normaliseAsks(asksB);
	if (asksA2.length === 0 || asksB2.length === 0) return [];

	const breakPoints = new Set();
	let cumulative = 0;
	for (const ask of asksA2) {
		cumulative += ask.size;
		breakPoints.add(cumulative);
	}
	cumulative = 0;
	for (const ask of asksB2) {
		cumulative += ask.size;
		breakPoints.add(cumulative);
	}

	const sorted = Array.from(breakPoints)
		.filter((q) => Number.isFinite(q) && q >= DEFAULTS.minOrderSize)
		.sort((a, b) => a - b);

	const ranges = [];
	let current = null;
	let previousQuantity = 0;

	for (const quantity of sorted) {
		const levelA = getLevelAtQuantity(asksA2, quantity);
		const levelB = getLevelAtQuantity(asksB2, quantity);
		if (!levelA || !levelB) break;

		const costA = levelA.cost;
		const costB = levelB.cost;
		const grossCost = (costA + costB) / quantity;
		const feePerShare = grossCost * (feeBps / 10_000);
		const totalCost = grossCost + feePerShare;
		const profitable = totalCost < 1;

		const candidate = {
			minQuantity: previousQuantity + 1,
			maxQuantity: quantity,
			priceA: costA / quantity,
			priceB: costB / quantity,
			marginalA: levelA.price,
			marginalB: levelB.price,
			costA,
			costB,
			grossCost,
			feePerShare,
			feeBps,
			totalCost,
			profit: 1 - totalCost,
		};

		if (profitable) {
			if (!current) {
				current = candidate;
			} else if (
				Math.abs(current.marginalA - candidate.marginalA) < 1e-12 &&
				Math.abs(current.marginalB - candidate.marginalB) < 1e-12
			) {
				current = { ...candidate, minQuantity: current.minQuantity };
			} else {
				ranges.push(current);
				current = candidate;
			}
		} else if (current) {
			ranges.push(current);
			current = null;
		}

		previousQuantity = quantity;
	}
	if (current) ranges.push(current);
	return ranges.map((range) => withMinimumCosts(range, asksA2, asksB2));
}

function buildMarketData(range, market, outcome) {
	const isA = outcome === 'YES';
	const maxCost = isA ? range.costA : range.costB;
	const minCost = isA ? range.minCostA : range.minCostB;
	return {
		name: market.name || `Market${outcome}`,
		outcome,
		price: round(maxCost / range.maxQuantity, 4),
		marginalPrice: round(isA ? range.marginalA : range.marginalB, 4),
		quantityAtPrice: range.maxQuantity,
		costUSD: round(maxCost, 2),
		timeToEnd: market.timeToEnd ?? null,
		quantityRange: {
			min: range.minQuantity,
			minCostUSD: round(minCost, 2),
			max: range.maxQuantity,
			maxCostUSD: round(maxCost, 2),
		},
	};
}

function buildProfitAnalysis(range) {
	const maxCostA = range.costA;
	const maxCostB = range.costB;
	const minCostA = range.minCostA;
	const minCostB = range.minCostB;
	const maxGrossPerShare = (maxCostA + maxCostB) / range.maxQuantity;
	const minGrossPerShare = (minCostA + minCostB) / range.minQuantity;
	const maxFeePerShare = maxGrossPerShare * (range.feeBps / 10_000);
	const minFeePerShare = minGrossPerShare * (range.feeBps / 10_000);
	const maxCostPerShare = maxGrossPerShare + maxFeePerShare;
	const minCostPerShare = minGrossPerShare + minFeePerShare;
	const maxTotalCost = maxCostA + maxCostB + maxFeePerShare * range.maxQuantity;
	const minTotalCost = minCostA + minCostB + minFeePerShare * range.minQuantity;

	return {
		grossCostPerShare: round(maxGrossPerShare, 4),
		feeBps: range.feeBps,
		feePerShare: round(maxFeePerShare, 4),
		costPerShare: round(maxCostPerShare, 4),
		profitPerShare: round(1 - maxCostPerShare, 4),
		profitPercentage: round(((1 - maxCostPerShare) / maxCostPerShare) * 100, 2),
		roi: round(((1 - maxCostPerShare) / maxCostPerShare) * 100, 2),
		grossRoi: round(((1 - maxGrossPerShare) / maxGrossPerShare) * 100, 2),
		minQuantity: range.minQuantity,
		minTotalCostUSD: round(minTotalCost, 2),
		minTotalProfitUSD: round(range.minQuantity - minTotalCost, 2),
		minPayoutUSD: range.minQuantity,
		maxQuantity: range.maxQuantity,
		maxTotalCostUSD: round(maxTotalCost, 2),
		maxTotalProfitUSD: round(range.maxQuantity - maxTotalCost, 2),
		maxPayoutUSD: range.maxQuantity,
		breakEvenProbability: round(maxCostPerShare, 4),
		edgeOverMarket: `${round((1 - maxCostPerShare) * 100, 2)}%`,
	};
}

function buildStrategyResult(range, marketA, marketB, outcomeA, outcomeB) {
	return {
		strategy: `${outcomeA} on ${marketA.name || 'MarketA'} + ${outcomeB} on ${marketB.name || 'MarketB'}`,
		marketA: {
			...buildMarketData(range, marketA, outcomeA),
			url: marketA.url ?? null,
		},
		marketB: {
			...buildMarketData(range, marketB, outcomeB),
			url: marketB.url ?? null,
		},
		profitAnalysis: buildProfitAnalysis(range),
		profitable: true,
	};
}

function calculateBestSurebet(orderbookA, orderbookB, marketA = {}, marketB = {}, options = {}) {
	if (!orderbookA || !orderbookB) return [];
	const results = [];

	const asksYesA = normaliseAsks(orderbookA.YES?.asks);
	const asksNoB = normaliseAsks(orderbookB.NO?.asks);
	if (asksYesA.length && asksNoB.length) {
		for (const range of findQuantityRanges(asksYesA, asksNoB, options)) {
			results.push(buildStrategyResult(range, marketA, marketB, 'YES', 'NO'));
		}
	}

	const asksNoA = normaliseAsks(orderbookA.NO?.asks);
	const asksYesB = normaliseAsks(orderbookB.YES?.asks);
	if (asksNoA.length && asksYesB.length) {
		for (const range of findQuantityRanges(asksNoA, asksYesB, options)) {
			results.push(buildStrategyResult(range, marketA, marketB, 'NO', 'YES'));
		}
	}

	return results.sort((a, b) => b.profitAnalysis.profitPercentage - a.profitAnalysis.profitPercentage);
}

function readMonitoredMarkets() {
	try {
		const value = loadJson(path.join(ROOT, 'data/sample/monitoredMarkets.json'));
		return Array.isArray(value) ? value : [];
	} catch {
		return [];
	}
}

async function checkMonitoredMarkets(futuurClient, polymarketClient, options = {}) {
	const results = [];
	const missingMarkets = [];
	const closedMarkets = [];
	const monitoredMarkets = readMonitoredMarkets();

	for (const match of monitoredMarkets) {
		const [clientAName, clientBName] = Object.keys(match);
		const marketAId = match[clientAName];
		const marketBId = match[clientBName];

		const clientA = clientAName === 'polymarket' ? polymarketClient : clientAName === 'futuur' ? futuurClient : null;
		const clientB = clientBName === 'polymarket' ? polymarketClient : clientBName === 'futuur' ? futuurClient : null;
		if (!clientA || !clientB) {
			missingMarkets.push(`unsupported client pair: ${clientAName}/${clientBName}`);
			continue;
		}

		const marketA = clientA.getMarketById(marketAId);
		const marketB = clientB.getMarketById(marketBId);
		if (!marketA || !marketB || marketA.closed || marketB.closed) {
			closedMarkets.push({ marketAId, marketBId });
			continue;
		}

		try {
			const orderbookA = await clientA.getOrderbook(marketA);
			const orderbookB = await clientB.getOrderbook(marketB);
			if (!orderbookA || !orderbookB) {
				missingMarkets.push({
					marketA: clientA.getMarketUrl?.(marketA) ?? String(marketAId),
					marketB: clientB.getMarketUrl?.(marketB) ?? String(marketBId),
				});
				continue;
			}
			results.push(...calculateBestSurebet(orderbookA, orderbookB, {
				name: clientAName,
				timeToEnd: marketA.endDate,
				title: marketA.title || marketA.name,
				url: clientA.getMarketUrl?.(marketA),
			}, {
				name: clientBName,
				timeToEnd: marketB.endDate,
				title: marketB.title || marketB.name,
				url: clientB.getMarketUrl?.(marketB),
			}, options));
		} catch (error) {
			missingMarkets.push({
				marketA: clientA.getMarketUrl?.(marketA) ?? String(marketAId),
				marketB: clientB.getMarketUrl?.(marketB) ?? String(marketBId),
				error: error.message,
			});
		}
	}

	return { results, missingMarkets, closedMarkets };
}

function runReplay(inputFile, outputFile, options) {
	const pair = loadJson(inputFile);
	const results = calculateBestSurebet(
		pair.orderbookA,
		pair.orderbookB,
		{ name: 'futuur', url: 'https://futuur.com/' },
		{ name: 'polymarket', url: 'https://polymarket.com/' },
		options,
	);
	const report = {
		generatedAt: new Date().toISOString(),
		source: path.relative(ROOT, inputFile),
		assumptions: {
			books: 'incremental ask levels',
			feeBps: options.feeBps,
			minOrderSize: DEFAULTS.minOrderSize,
			excluded: ['settlement risk', 'capital lockup', 'withdrawal costs'],
		},
		results,
	};
	writeJson(outputFile, report);
	return report;
}

async function runLive(outputFile, options) {
	const futuurClient = new FutuurClient();
	await futuurClient.init();
	const polymarketClient = new PolymarketClient();
	await polymarketClient.init();
	const report = await checkMonitoredMarkets(futuurClient, polymarketClient, options);
	const payload = {
		generatedAt: new Date().toISOString(),
		source: 'live venue order books',
		assumptions: {
			books: 'incremental ask levels',
			feeBps: options.feeBps,
			minOrderSize: DEFAULTS.minOrderSize,
			excluded: ['settlement risk', 'capital lockup', 'withdrawal costs'],
		},
		...report,
	};
	writeJson(outputFile, payload);
	return payload;
}

function usage() {
	console.log(`Usage:
  bun main.js --replay ../../data/sample/orderbook_pair.json --out ../../results/sample/capacity_output.json
  bun main.js --live --out ../../results/live_surebet.json
  bun main.js --replay <file> --fee-bps 100 --out <file>`);
}

async function main() {
	const args = parseArgs(process.argv);
	const options = {
		feeBps: Number(args['fee-bps'] ?? DEFAULTS.feeBps),
	};
	if (!Number.isFinite(options.feeBps) || options.feeBps < 0) {
		throw new Error('--fee-bps must be a non-negative number');
	}

	if (args.replay) {
		const input = path.resolve(process.cwd(), String(args.replay));
		const output = path.resolve(process.cwd(), String(args.out ?? path.join(ROOT, 'results/sample/capacity_output.json')));
		const report = runReplay(input, output, options);
		console.log(JSON.stringify(report.results, null, 2));
		console.error(`Wrote ${path.relative(process.cwd(), output)}`);
		return;
	}

	if (args.live) {
		const output = path.resolve(process.cwd(), String(args.out ?? path.join(ROOT, 'results/live_surebet.json')));
		const report = await runLive(output, options);
		console.log(JSON.stringify(report.results, null, 2));
		console.error(`Wrote ${path.relative(process.cwd(), output)}`);
		return;
	}

	usage();
	process.exitCode = 1;
}

if (require.main === module) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}

module.exports = {
	findQuantityRanges,
	calculateBestSurebet,
	checkMonitoredMarkets,
	runReplay,
	runLive,
};
