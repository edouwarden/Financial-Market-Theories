import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'amazon-adoption.json');

export async function amazonsell() {
	const url = 'https://real-time-amazon-data.p.rapidapi.com/search?query=wallet%20crypto&page=1&country=US&sort_by=RELEVANCE&product_condition=ALL&is_prime=false&deals_and_discounts=NONE';
	const options = {
		method: 'GET',
		headers: {
			'x-rapidapi-key': process.env.RAPIDAPI_KEY,
			'x-rapidapi-host': 'real-time-amazon-data.p.rapidapi.com'
		}
	};

	const response = await fetch(url, options);
	if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
	const result = await response.json();
	const count = result.data.total_products;
	const products = Array.isArray(result.data.products) ? result.data.products : [];
	let totalSold = 0;
	let productsWithSales = 0;
	for (const product of products) {
		let volume = product.sales_volume;
		if (!volume) continue;
		volume = volume.replace('+ bought in past month', '');
		if (volume.includes('K')) {
			volume = volume.replace('K', '');
			volume = parseFloat(volume) * 1000;
		} else
			volume = parseFloat(volume);
		if (!Number.isFinite(volume)) continue;
		totalSold += volume;
		productsWithSales += 1;
	}

	// The search reports total_products for the whole query, but sales_volume is
	// only available for the page-1 products we actually parsed. Dividing by the
	// search-result count would understate average sales by orders of magnitude,
	// so use the number of listed products on the page as the denominator.
	const avgSoldPerListedProduct =
		products.length > 0 ? totalSold / products.length : 0;

	const report = {
		title: 'Amazon Sell for wallet crypto',
		query: 'wallet crypto',
		totalProducts: count,
		productCount: products.length,
		productsWithSales,
		totalSold,
		avgSoldPerListedProduct,
		source: 'Data from Amazon Data via RapidAPI',
		generatedAt: new Date().toISOString()
	};

	await mkdir(RESULTS_DIR, { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));

	return report;
}

async function main() {
	const report = await amazonsell();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
