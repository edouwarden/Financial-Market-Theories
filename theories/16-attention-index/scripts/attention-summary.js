/**
 * Summarise the committed Google News attention sample.
 *
 * This is a data-quality report, not a lead-lag test. It answers: how many
 * observations are there, what period do they cover, where are the gaps, and
 * what does the recent level look like?
 */

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SAMPLE_FILE = join(HERE, '../data/sample/google-news.json');
const OUT_FILE = join(HERE, '../results/google-news-summary.json');

const DAY_MS = 24 * 60 * 60 * 1000;

export async function attentionSummary() {
	const raw = JSON.parse(await readFile(SAMPLE_FILE, 'utf8'));
	if (!Array.isArray(raw)) throw new Error('Sample is not an array');

	const rows = raw
		.filter((row) => row && typeof row.timestamp === 'string' && Number.isFinite(row.totalHits))
		.map((row) => ({ timestamp: new Date(row.timestamp), totalHits: row.totalHits }))
		.filter((row) => !Number.isNaN(row.timestamp.valueOf()))
		.sort((a, b) => a.timestamp - b.timestamp);

	if (rows.length === 0) throw new Error('Sample has no usable observations');

	const values = rows.map((row) => row.totalHits);
	const first = rows[0];
	const last = rows[rows.length - 1];
	const dayKeys = new Set(rows.map((row) => row.timestamp.toISOString().slice(0, 10)));
	const spanDays = Math.round((last.timestamp - first.timestamp) / DAY_MS) + 1;
	const gaps = [];
	for (let i = 1; i < rows.length; i += 1) {
		const delta = Math.round((rows[i].timestamp - rows[i - 1].timestamp) / DAY_MS);
		if (delta > 1) {
			gaps.push({
				after: rows[i - 1].timestamp.toISOString(),
				before: rows[i].timestamp.toISOString(),
				missingDays: delta - 1,
			});
		}
	}

	const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
	const last30 = rows.filter((row) => last.timestamp - row.timestamp <= 30 * DAY_MS);
	const previous30 = rows.filter((row) => {
		const age = last.timestamp - row.timestamp;
		return age > 30 * DAY_MS && age <= 60 * DAY_MS;
	});
	const average = (list) =>
		list.length ? list.reduce((sum, row) => sum + row.totalHits, 0) / list.length : null;

	const report = {
		source: 'data/sample/google-news.json',
		generatedAt: new Date().toISOString(),
		coverage: {
			observations: rows.length,
			distinctDays: dayKeys.size,
			first: first.timestamp.toISOString(),
			last: last.timestamp.toISOString(),
			spanDays,
			missingDays: Math.max(0, spanDays - dayKeys.size),
		},
		distribution: {
			min: Math.min(...values),
			max: Math.max(...values),
			mean: Number(mean.toFixed(2)),
			median: Number(
				[...values].sort((a, b) => a - b)[Math.floor(values.length / 2)].toFixed(2)
			),
			last: last.totalHits,
		},
		recent: {
			last30Mean: average(last30) === null ? null : Number(average(last30).toFixed(2)),
			previous30Mean:
				average(previous30) === null ? null : Number(average(previous30).toFixed(2)),
			change30dPct:
				average(previous30) === null || average(previous30) === 0
					? null
					: Number((((average(last30) - average(previous30)) / average(previous30)) * 100).toFixed(2)),
		},
		gaps,
		caveats: [
			'Google News hit counts are a proxy for news volume, not sentiment.',
			'The sample is not joined to prices, volume, or on-chain activity.',
			'This report does not test lead-lag or a tradeable signal.',
		],
	};

	await mkdir(dirname(OUT_FILE), { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));
	return report;
}

async function main() {
	const report = await attentionSummary();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
