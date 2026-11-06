#!/usr/bin/env bun
/**
 * Offline crypto news-cluster report.
 *
 * Reads the safe sample in data/sample/ and prints/writes the clusters that the
 * live collector would maintain. This is a demonstration of the clustering
 * rule, not evidence of forward returns.
 *
 * Usage:
 *   bun scripts/cluster-report.js
 *   bun scripts/cluster-report.js --out results/cluster_report.json
 */

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const MENTIONS_FILE = path.join(ROOT, 'data/sample/mentions.json');
const ITEMS_FILE = path.join(ROOT, 'data/sample/items.json');
const DEFAULT_OUT = path.join(ROOT, 'results/cluster_report.json');
const WINDOW_MINUTES = 20;

function loadJson(file, fallback) {
	try {
		return JSON.parse(fs.readFileSync(file, 'utf8'));
	} catch {
		return fallback;
	}
}

function overlapCount(a, b) {
	return a.filter((value) => b.includes(value)).length;
}

function isSimilar(a, b) {
	if (a.twitterLink && b.twitterLink && a.twitterLink === b.twitterLink) return true;
	if (a.websiteLink && b.websiteLink && a.websiteLink === b.websiteLink) return true;
	const keywordsA = a.keywords ?? [];
	const keywordsB = b.keywords ?? [];
	const overlap = overlapCount(keywordsA, keywordsB);
	const minLength = Math.min(keywordsA.length, keywordsB.length);
	return minLength < 3 ? overlap >= 2 : overlap >= 3;
}

function buildClusters(mentions) {
	const clusters = [];
	for (const mention of mentions) {
		const cluster = clusters.find((candidate) => candidate.mentions.some((existing) => isSimilar(existing, mention)));
		if (cluster) cluster.mentions.push(mention);
		else clusters.push({ mentions: [mention] });
	}

	return clusters
		.map((cluster) => {
			const timestamps = cluster.mentions.flatMap((mention) => mention.timestamps ?? []).sort((a, b) => a - b);
			const keywords = [...new Set(cluster.mentions.flatMap((mention) => mention.keywords ?? []))].sort();
			return {
				records: cluster.mentions.length,
				timestamps: timestamps.length,
				keywords,
				firstSeen: timestamps[0] ? new Date(timestamps[0]).toISOString() : null,
				lastSeen: timestamps.at(-1) ? new Date(timestamps.at(-1)).toISOString() : null,
				spanMinutes: timestamps.length > 1 ? Number(((timestamps.at(-1) - timestamps[0]) / 60_000).toFixed(2)) : 0,
				twitterLink: cluster.mentions.find((mention) => mention.twitterLink)?.twitterLink ?? null,
				websiteLink: cluster.mentions.find((mention) => mention.websiteLink)?.websiteLink ?? null,
			};
		})
		.sort((a, b) => b.timestamps - a.timestamps);
}

function main() {
	const args = process.argv.slice(2);
	const outIndex = args.indexOf('--out');
	const outFile = outIndex >= 0 && args[outIndex + 1] ? path.resolve(process.cwd(), args[outIndex + 1]) : DEFAULT_OUT;

	const mentions = loadJson(MENTIONS_FILE, []);
	const items = loadJson(ITEMS_FILE, []);
	const clusters = buildClusters(mentions);
	const report = {
		generatedAt: new Date().toISOString(),
		source: path.relative(ROOT, MENTIONS_FILE),
		windowMinutes: WINDOW_MINUTES,
		mentionCount: mentions.length,
		totalTimestamps: mentions.reduce((sum, mention) => sum + (mention.timestamps?.length ?? 0), 0),
		itemCount: items.length,
		clusterCount: clusters.length,
		clusters,
	};

	fs.mkdirSync(path.dirname(outFile), { recursive: true });
	fs.writeFileSync(outFile, JSON.stringify(report, null, 2));
	console.log(JSON.stringify(report, null, 2));
	console.error(`Wrote ${path.relative(process.cwd(), outFile)}`);
}

if (require.main === module) main();

module.exports = { buildClusters, isSimilar };
