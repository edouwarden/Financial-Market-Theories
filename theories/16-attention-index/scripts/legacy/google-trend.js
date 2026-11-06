import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'google-trends.json');

const sleep = (ms) => new Promise(resolveSleep => setTimeout(resolveSleep, ms));

async function createGoogleTrends(keyword) {
	const url = `https://targeted-keyword-trend.p.rapidapi.com/${keyword}`;
	const options = {
		method: 'GET',
		headers: {
			'x-rapidapi-key': process.env.RAPIDAPI_KEY,
			'x-rapidapi-host': 'targeted-keyword-trend.p.rapidapi.com'
		}
	};

	try {
		const response = await fetch(url, options);
		if (!response.ok) {
			console.error('Error fetching Google Trends:', response.statusText);
			if (response.statusText.includes('Gateway Time-out'))
				return { status: 2 };
			return { status: 0 };
		}
		const result = await response.json();

		// Ensure result is in the expected format
		const trendsData = Array.isArray(result) ? result.slice(2) :
			(result.data ? result.data : []);

		if (trendsData.length === 0)
			return { status: 0 };

		// Extract labels and data for the chart
		const labels = trendsData.map(item => item.Month_Date_Year).slice(-12); // Last 12 months
		const data = trendsData.map(item => item.Search_Count).slice(-12); // Last 12 months

		// Create QuickChart URL
		const chartConfig = {
			type: 'line',
			data: {
				labels: labels,
				datasets: [{
					label: `Google Trends: ${keyword}`,
					data: data,
					borderColor: 'rgb(75, 192, 192)',
					backgroundColor: 'rgba(75, 192, 192, 0.2)',
					fill: true,
					tension: 0.4
				}]
			},
			options: {
				responsive: true,
				plugins: {
					title: {
						display: true,
						text: `Google Trends for "${keyword}"`
					}
				},
				scales: {
					y: {
						beginAtZero: true,
						title: {
							display: true,
							text: 'Search Interest (0-100)'
						}
					}
				}
			}
		};

		const quickChartUrl = `https://quickchart.io/chart?c=${encodeURIComponent(JSON.stringify(chartConfig))}&width=800&height=400`;

		return {
			status: 1,
			keyword: keyword,
			chartUrl: quickChartUrl,
			data: trendsData
		};

	} catch (error) {
		console.error('Error fetching Google Trends:', error);
		if (error.message.includes('Gateway Time-out'))
			return { status: 2 };
		return { status: 0 };
	}
}

export async function sendGoogleTrends() {
	// Example keyword - you can modify this or make it dynamic
	const keywords = ['bitcoin', 'ethereum', 'altcoin', 'crypto'];
	const results = [];

	for (const keyword of keywords) {
		let trendsData = null;
		for (let i = 0; i < 3; i++) {
			trendsData = await createGoogleTrends(keyword);
			await sleep(2000);
			if (trendsData.status === 1) break;
			if (trendsData.status === 2) break;
		}

		if (!trendsData || trendsData.status !== 1) {
			results.push({
				keyword,
				status: trendsData?.status === 2 ? 'timeout' : 'no-data',
				description: `No data found for "${keyword}"`
			});
			if (trendsData?.status === 2) break;
			continue;
		}

		results.push({
			keyword,
			status: 'ok',
			title: `📈 Google Trends: ${trendsData.keyword}`,
			description: `Search interest over time for "${trendsData.keyword}"`,
			chartUrl: trendsData.chartUrl,
			data: trendsData.data,
			source: 'Data from Google Trends via RapidAPI'
		});
	}

	const report = {
		source: 'Google Trends via RapidAPI',
		results,
		generatedAt: new Date().toISOString()
	};

	await mkdir(RESULTS_DIR, { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));

	return report;
}

async function main() {
	const report = await sendGoogleTrends();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
