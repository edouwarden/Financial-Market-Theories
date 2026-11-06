import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'tradingview-indicators.json');

function analyzeMAs(data) {
	const signals = [];
	const price = data.close;

	// EMA Analysis
	if (price > data.EMA200 && price > data.EMA50 && data.EMA20 > data.EMA50) {
		signals.push("🟢 EMA: Strong Uptrend - Price above EMA200 & EMA50, EMA20 above EMA50");
	} else if (price < data.EMA200 && price < data.EMA50 && data.EMA20 < data.EMA50) {
		signals.push("🔴 EMA: Strong Downtrend - Price below EMA200 & EMA50, EMA20 below EMA50");
	} else {
		signals.push("⚪ EMA: Mixed signals - No clear trend");
	}

	// SMA Analysis
	if (price > data.SMA200 && data.SMA20 > data.SMA50) {
		signals.push("🟢 SMA: Bullish - Price above SMA200, SMA20 above SMA50");
	} else if (price < data.SMA200 && data.SMA20 < data.SMA50) {
		signals.push("🔴 SMA: Bearish - Price below SMA200, SMA20 below SMA50");
	} else {
		signals.push("⚪ SMA: Mixed signals");
	}

	return signals;
}

function analyzeOscillators(data) {
	const signals = [];

	// RSI Analysis
	if (data.RSI > 70) {
		signals.push("🔴 RSI: Overbought at " + data.RSI.toFixed(2));
	} else if (data.RSI < 30) {
		signals.push("🟢 RSI: Oversold at " + data.RSI.toFixed(2));
	} else {
		signals.push("⚪ RSI: Neutral at " + data.RSI.toFixed(2));
	}

	// Stochastic Analysis
	if (data["Stoch.K"] > 80 && data["Stoch.D"] > 80) {
		signals.push("🔴 Stochastic: Overbought");
	} else if (data["Stoch.K"] < 20 && data["Stoch.D"] < 20) {
		signals.push("🟢 Stochastic: Oversold");
	} else {
		signals.push("⚪ Stochastic: Neutral");
	}

	// CCI Analysis
	if (data.CCI20 > 100) {
		signals.push("🔴 CCI: Overbought at " + data.CCI20.toFixed(2));
	} else if (data.CCI20 < -100) {
		signals.push("🟢 CCI: Oversold at " + data.CCI20.toFixed(2));
	} else {
		signals.push("⚪ CCI: Neutral at " + data.CCI20.toFixed(2));
	}

	return signals;
}

function analyzeTrend(data) {
	const signals = [];

	// ADX Analysis
	if (data.ADX > 25) {
		if (data["ADX+DI"] > data["ADX-DI"]) {
			signals.push("🟢 ADX: Strong Uptrend - ADX: " + data.ADX.toFixed(2));
		} else {
			signals.push("🔴 ADX: Strong Downtrend - ADX: " + data.ADX.toFixed(2));
		}
	} else {
		signals.push("⚪ ADX: No Strong Trend - ADX: " + data.ADX.toFixed(2));
	}

	// MACD Analysis
	if (data["MACD.macd"] > data["MACD.signal"]) {
		signals.push("🟢 MACD: Bullish Crossover");
	} else if (data["MACD.macd"] < data["MACD.signal"]) {
		signals.push("🔴 MACD: Bearish Crossover");
	} else {
		signals.push("⚪ MACD: Neutral");
	}

	// Awesome Oscillator
	if (data.AO > 0 && data.AO > data["AO[1]"]) {
		signals.push("🟢 AO: Bullish - Increasing");
	} else if (data.AO < 0 && data.AO < data["AO[1]"]) {
		signals.push("🔴 AO: Bearish - Decreasing");
	} else {
		signals.push("⚪ AO: Mixed signals");
	}

	return signals;
}

function toRecommendation(value) {
	if (value > 0) return 'BUY';
	if (value < 0) return 'SELL';
	return 'NEUTRAL';
}

async function analyzeSymbol(symbol) {
	const url = `https://trading-real-time.p.rapidapi.com/technicals/summary?query=BINANCE%3A${symbol}.P`;
	const options = {
		method: 'GET',
		headers: {
			'x-rapidapi-key': process.env.RAPIDAPI_KEY,
			'x-rapidapi-host': 'trading-real-time.p.rapidapi.com'
		}
	};

	const response = await fetch(url, options);
	const result = await response.json();

	if (!result.status || !result.data) {
		console.error('Error fetching trading view indicators:', result);
		return null;
	}

	const data = result.data;

	// Analyze all indicators
	const maSignals = analyzeMAs(data);
	const oscillatorSignals = analyzeOscillators(data);
	const trendSignals = analyzeTrend(data);

	return {
		symbol,
		price: data.close,
		movingAverages: maSignals,
		oscillators: oscillatorSignals,
		trend: trendSignals,
		recommendation: {
			movingAverages: toRecommendation(data["Recommend.MA"]),
			oscillators: toRecommendation(data["Recommend.Other"]),
			summary: toRecommendation(data["Recommend.All"])
		},
		fetchedAt: new Date().toISOString()
	};
}

export async function tradingviewIndicators() {
	const symbols = ['BTCUSDT', 'ETHUSDT'];
	const results = [];

	for (const symbol of symbols) {
		const analysis = await analyzeSymbol(symbol);
		if (analysis) results.push(analysis);
	}

	const report = {
		title: '🎯 Trading View Technical Analysis',
		symbols,
		results
	};

	await mkdir(RESULTS_DIR, { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));

	return report;
}

async function main() {
	const report = await tradingviewIndicators();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
