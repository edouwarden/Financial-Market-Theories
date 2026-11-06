import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'wallstreetbets.json');

export async function wsb() {
	const url = 'https://reddit3.p.rapidapi.com/v1/reddit/posts?url=https%3A%2F%2Fwww.reddit.com%2Fr%2Fwallstreetbets&filter=hot';
	const options = {
		method: 'GET',
		headers: {
			'x-rapidapi-key': process.env.RAPIDAPI_KEY,
			'x-rapidapi-host': 'reddit3.p.rapidapi.com'
		}
	};

	const response = await fetch(url, options);
	const result = await response.json();
	const posts = result.body;

	const selectedPosts = (posts || []).slice(0, 8).map(post => ({
		title: post.title.slice(0, 256),
		content: post.selftext ? post.selftext.slice(0, 500) : '(No content)',
		url: post.url ?? null,
		author: post.author ?? null,
		score: post.score ?? null
	}));

	const report = {
		title: 'Wall Street Bets',
		description: 'Latest posts from Wall Street Bets',
		posts: selectedPosts,
		message: selectedPosts.length > 0 ? null : 'Aucun post trouvé.',
		source: 'Data from Reddit via RapidAPI',
		generatedAt: new Date().toISOString()
	};

	await mkdir(RESULTS_DIR, { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));

	return report;
}

async function main() {
	const report = await wsb();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
