import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'ideas.json');

export async function tradingviewIdea() {
	const url = 'https://trading-real-time.p.rapidapi.com/ideas/list?category=crypto';
	const options = {
		method: 'GET',
		headers: {
			'x-rapidapi-key': process.env.RAPIDAPI_KEY,
			'x-rapidapi-host': 'trading-real-time.p.rapidapi.com'
		}
	};

	const response = await fetch(url, options);
	if (!response.ok)
		throw new Error('Failed to fetch trading view ideas');

	const result = await response.json();
	if (!result.data || !result.data.results || result.data.results.length === 0)
		throw new Error('Failed to fetch trading view ideas 2');

	const ideas = result.data.results.filter(item => new Date(item.created_at) > new Date(Date.now() - 1000 * 60 * 60 * 24 * 7) || new Date(item.updated_at) > new Date(Date.now() - 1000 * 60 * 60 * 24 * 7));

	const report = {
		title: 'Trading View Ideas',
		periodDays: 7,
		count: ideas.length,
		ideas
	};

	await mkdir(RESULTS_DIR, { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));

	if (ideas.length === 0)
		console.log('No ideas found');

	return report;
}

async function main() {
	const report = await tradingviewIdea();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
