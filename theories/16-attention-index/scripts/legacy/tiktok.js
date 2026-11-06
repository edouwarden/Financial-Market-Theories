import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'tiktok-tracker.json');

export async function tiktok() {
	const url = 'https://tiktok-shop2.p.rapidapi.com/api/v1/search/hashtag?keyword=bitcoin&offset=0&count=10';
	const options = {
		method: 'GET',
		headers: {
			'x-rapidapi-key': process.env.RAPIDAPI_KEY,
			'x-rapidapi-host': 'tiktok-shop2.p.rapidapi.com'
		}
	};

	const response = await fetch(url, options);
	const result = await response.json();
	const challenge = result.challenge_list[0].challenge_info;
	const use_count = challenge.use_count;
	const user_count = challenge.user_count;
	const view_count = challenge.view_count;

	const report = {
		title: 'TikTok Tracker',
		description: `Use count: ${use_count}\n👤User count: ${user_count}\n👀View count: ${view_count}`,
		challenge,
		useCount: use_count,
		userCount: user_count,
		viewCount: view_count,
		source: 'Data from TikTok Shop via RapidAPI',
		generatedAt: new Date().toISOString()
	};

	await mkdir(RESULTS_DIR, { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));

	return report;
}

async function main() {
	const report = await tiktok();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
