#!/usr/bin/env bun
/**
 * Binance leaderboard positioning collector.
 *
 * This is a data-collection prototype for the crowding hypothesis, not a
 * backtest. It fetches public perpetual positions for a fixed panel, aggregates
 * long/short leverage by symbol, and appends BTC/ETH snapshots to a local
 * history file.
 *
 * The repository ships a synthetic example panel only. To run it against live
 * data, put your own encrypted UIDs in `data/private/traders.json` (gitignored)
 * or point `TRADERS_FILE` at a private file.
 *
 * Usage:
 *   RAPIDAPI_KEY=... bun scripts/toptrader.js
 */

const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.join(__dirname, "..");
const API_KEY = process.env.RAPIDAPI_KEY;
const SNAPSHOT_FILE = path.join(ROOT, "results/leaderboard_snapshot.json");
const HISTORY_FILE = path.join(ROOT, "results/leverage_history.json");
const HISTORY_LIMIT = 5000;

// Synthetic examples. They are intentionally not valid Binance UIDs.
const EXAMPLE_TRADERS = [
	{ id: 1, uid: "EXAMPLE_UID_001", username: "example_trader_1" },
	{ id: 2, uid: "EXAMPLE_UID_002", username: "example_trader_2" },
	{ id: 3, uid: "EXAMPLE_UID_003", username: "example_trader_3" },
	{ id: 4, uid: "EXAMPLE_UID_004", username: "example_trader_4" },
	{ id: 5, uid: "EXAMPLE_UID_005", username: "example_trader_5" },
];

function loadTraders() {
	const file = process.env.TRADERS_FILE || path.join(ROOT, "data/private/traders.json");
	if (!fs.existsSync(file)) return { traders: EXAMPLE_TRADERS, source: "synthetic example panel", file: null };
	const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
	const traders = Array.isArray(parsed) ? parsed : parsed.traders;
	if (!Array.isArray(traders)) throw new Error(`${file} must contain an array or { traders: [...] }`);
	return { traders, source: "private panel", file };
}

async function getUserPosition(uid) {
	const url = `https://binance-futures-leaderboard1.p.rapidapi.com/v1/getOtherPosition?encryptedUid=${encodeURIComponent(uid)}&tradeType=PERPETUAL`;
	const response = await fetch(url, {
		method: "GET",
		headers: {
			"x-rapidapi-key": API_KEY,
			"x-rapidapi-host": "binance-futures-leaderboard1.p.rapidapi.com",
		},
	});
	if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
	const payload = await response.json();
	const positions = payload?.data?.otherPositionRetList;
	if (!Array.isArray(positions)) throw new Error("unexpected response shape: missing data.otherPositionRetList");
	return positions;
}

function normaliseSymbol(symbol) {
	const specialCases = ["BTCDOM", "ETHDOM", "DEFIDOM", "ALTDOM"];
	if (specialCases.some((special) => symbol.startsWith(special))) return symbol;
	const quoteCurrencies = ["USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USD", "PERP"];
	for (const quote of quoteCurrencies) {
		if (symbol.endsWith(quote)) return symbol.slice(0, -quote.length);
	}
	return symbol;
}

function processPositions(positions) {
	const symbolStats = {};
	const totalStats = { pnl: 0, positions: 0, short: 0, long: 0, volume: 0, longLev: 0, shortLev: 0 };

	for (const position of positions) {
		const symbol = normaliseSymbol(position.symbol);
		const isShort = position.amount < 0;
		const volume = Math.abs(position.amount * position.markPrice);

		if (!symbolStats[symbol]) {
			symbolStats[symbol] = {
				positions: 0,
				shortPositions: 0,
				longPositions: 0,
				totalPnL: 0,
				totalVolume: 0,
				levLongSum: 0,
				levShortSum: 0,
				avgLongLev: 0,
				avgShortLev: 0,
				levDelta: 0,
				longShortRatio: null,
			};
		}

		const stats = symbolStats[symbol];
		stats.positions += 1;
		stats.totalPnL += position.pnl;
		stats.totalVolume += volume;
		if (isShort) {
			stats.shortPositions += 1;
			stats.levShortSum += position.leverage;
			totalStats.short += 1;
			totalStats.shortLev += position.leverage;
		} else {
			stats.longPositions += 1;
			stats.levLongSum += position.leverage;
			totalStats.long += 1;
			totalStats.longLev += position.leverage;
		}

		totalStats.pnl += position.pnl;
		totalStats.positions += 1;
		totalStats.volume += volume;
	}

	for (const stats of Object.values(symbolStats)) {
		stats.avgLongLev = stats.longPositions ? stats.levLongSum / stats.longPositions : 0;
		stats.avgShortLev = stats.shortPositions ? stats.levShortSum / stats.shortPositions : 0;
		stats.levDelta = stats.avgLongLev - stats.avgShortLev;
		stats.longShortRatio = stats.shortPositions ? stats.longPositions / stats.shortPositions : null;
	}

	return {
		symbolStats,
		totalStats: {
			...totalStats,
			avgLongLev: totalStats.long ? totalStats.longLev / totalStats.long : 0,
			avgShortLev: totalStats.short ? totalStats.shortLev / totalStats.short : 0,
			longShortRatio: totalStats.short ? totalStats.long / totalStats.short : null,
		},
	};
}

function appendHistory(symbolStats) {
	let history = [];
	try {
		history = JSON.parse(fs.readFileSync(HISTORY_FILE, "utf8"));
		if (!Array.isArray(history)) history = [];
	} catch {
		history = [];
	}

	const pick = (symbol) => {
		const stats = symbolStats[symbol];
		if (!stats) return undefined;
		return {
			avgLongLev: stats.avgLongLev,
			avgShortLev: stats.avgShortLev,
			levDelta: stats.levDelta,
		};
	};

	history.push({ ts: Date.now(), BTC: pick("BTC"), ETH: pick("ETH") });
	history = history.slice(-HISTORY_LIMIT);
	fs.mkdirSync(path.dirname(HISTORY_FILE), { recursive: true });
	fs.writeFileSync(HISTORY_FILE, JSON.stringify(history, null, 2));
	return history;
}

async function collect() {
	if (!API_KEY) throw new Error("RAPIDAPI_KEY is required for live collection");

	const { traders, source, file } = loadTraders();
	const positions = [];
	const errors = [];

	for (const trader of traders) {
		try {
			const result = await getUserPosition(trader.uid);
			positions.push(...result);
		} catch (error) {
			errors.push({ trader: trader.id, error: error.message });
		}
		await Bun.sleep(500);
	}

	if (positions.length === 0) {
		throw new Error(`No positions returned. ${errors.length} trader requests failed; the example panel needs real UIDs.`);
	}

	const { symbolStats, totalStats } = processPositions(positions);
	const history = appendHistory(symbolStats);
	const snapshot = {
		generatedAt: new Date().toISOString(),
		source,
		panelFile: file ? path.relative(ROOT, file) : null,
		traderCount: traders.length,
		positionCount: positions.length,
		total: totalStats,
		symbols: symbolStats,
		historyPoints: history.length,
		errors,
		caveats: [
			"Leaderboards select survivors; this panel is not a random sample.",
			"Position size is not normalized by account equity.",
			"This collector does not test forward returns or funding.",
		],
	};

	fs.mkdirSync(path.dirname(SNAPSHOT_FILE), { recursive: true });
	fs.writeFileSync(SNAPSHOT_FILE, JSON.stringify(snapshot, null, 2));
	return snapshot;
}

if (require.main === module) {
	collect()
		.then((snapshot) => {
			console.log(JSON.stringify({
				generatedAt: snapshot.generatedAt,
				traderCount: snapshot.traderCount,
				positionCount: snapshot.positionCount,
				total: snapshot.total,
				historyPoints: snapshot.historyPoints,
				errors: snapshot.errors.length,
			}, null, 2));
			console.error(`Wrote ${path.relative(process.cwd(), SNAPSHOT_FILE)}`);
		})
		.catch((error) => {
			console.error(`Leaderboard collection failed: ${error.message}`);
			process.exitCode = 1;
		});
}

module.exports = { collect, processPositions, normaliseSymbol, loadTraders };
