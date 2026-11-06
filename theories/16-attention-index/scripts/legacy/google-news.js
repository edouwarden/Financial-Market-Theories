import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'google-news.json');
const SAMPLE_FILE = join(HERE, '../../data/sample/google-news.json');
const STATE_FILE = join(RESULTS_DIR, 'state/google-news.json');

export async function googleNews() {
	const url = 'https://news-api14.p.rapidapi.com/v2/search/articles?query=bitcoin&language=en&from=1d';
	const options = {
		method: 'GET',
		headers: {
			'x-rapidapi-key': process.env.RAPIDAPI_KEY,
			'x-rapidapi-host': 'news-api14.p.rapidapi.com'
		}
	};

	try {
		const response = await fetch(url, options);
		if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
		const result = await response.json();
		const total = result.totalHits;
		if (!Number.isFinite(total)) throw new Error('Response did not contain a numeric totalHits');

		let history = [];
		try {
			const parsed = JSON.parse(await readFile(SAMPLE_FILE, 'utf8'));
			if (Array.isArray(parsed)) history = parsed;
		} catch (error) {
			console.warn(`Could not read the committed sample: ${error.message}`);
		}

		const entry = { timestamp: new Date().toISOString(), totalHits: total };
		history = [...history, entry];

		// Never write live observations back into data/sample/. The sample is a
		// frozen provenance record; live state belongs under results/state/ and is
		// gitignored.
		await mkdir(join(RESULTS_DIR, 'state'), { recursive: true });
		await writeFile(STATE_FILE, JSON.stringify(history, null, 2));

		// Generate QuickChart URL
		const chartData = {
			type: 'line',
			data: {
				labels: history.slice(-50).map(item => new Date(item.timestamp).toLocaleTimeString()),
				datasets: [{
					label: 'Total Hits',
					data: history.slice(-50).map(item => item.totalHits),
					fill: false,
					borderColor: 'rgb(75, 192, 192)',
					tension: 0.1
				}]
			}
		};

		const chartUrl = `https://quickchart.io/chart?c=${encodeURIComponent(JSON.stringify(chartData))}`;

		const report = {
			title: 'Bitcoin News Total Hits',
			description: `Current total hits: ${total}`,
			totalHits: total,
			chartUrl,
			history: history.slice(-50),
			source: 'News API 14 via RapidAPI',
			generatedAt: entry.timestamp
		};

		await mkdir(RESULTS_DIR, { recursive: true });
		await writeFile(OUT_FILE, JSON.stringify(report, null, 2));

		return report;

	} catch (error) {
		console.error(error);
		throw error;
	}
}

async function main() {
	const report = await googleNews();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
