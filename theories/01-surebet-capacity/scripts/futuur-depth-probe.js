#!/usr/bin/env node
/**
 * Futuur depth probe.
 *
 * Futuur's public API returns a price, not a book. To see how the quoted price
 * changes with size, this renders the market page through ScrapingAnt, types a
 * sequence of stake sizes into the order form, and reads the "Price per share"
 * field after each change.
 *
 * The output is a price-by-size curve. It is a UI measurement, not a real L2
 * snapshot: it assumes the quote is executable and it rounds through the page's
 * display precision.
 *
 * Usage:
 *   RAPIDAPI_KEY=... node futuur-depth-probe.js <futuur-market-url> [output.json]
 */

const fs = require('node:fs');

const SIZES = [1, 5, 10, 50, 100, 250, 500, 1000];
const PROXY_COUNTRY = process.env.PROXY_COUNTRY || 'JP';

const target = process.argv[2];
const outputPath = process.argv[3];

if (!target) {
	console.error('Usage: RAPIDAPI_KEY=... node futuur-depth-probe.js <futuur-market-url> [output.json]');
	process.exit(1);
}

const apiKey = process.env.RAPIDAPI_KEY;
if (!apiKey) {
	console.error('Missing RAPIDAPI_KEY (ScrapingAnt).');
	process.exit(1);
}

const jsSnippet = `return new Promise(async resolve => {
	const sleep = ms => new Promise(r => setTimeout(r, ms));
	const getPrice = () => document.querySelector('div.text-xs:nth-child(1)')?.textContent?.trim() || '';
	const prices = { yes: {}, no: {} };

	for (const side of ['yes', 'no']) {
		if (side === 'no') {
			Array.from(document.querySelectorAll('button'))
				.find(b => b.querySelector('span.text-lg.font-medium')?.textContent?.trim() === 'No')?.click();
			await sleep(500);
		}
		for (const size of ${JSON.stringify(SIZES)}) {
			const input = document.querySelector('#place_bet_input');
			if (!input) break;
			input.value = size;
			input.dispatchEvent(new Event('input', { bubbles: true }));
			await sleep(100);
			prices[side][size] = getPrice();
		}
	}

	const div = document.createElement('div');
	div.id = 'scraped-prices';
	div.setAttribute('data-prices', btoa(JSON.stringify(prices)));
	div.style.display = 'none';
	document.body.appendChild(div);
	resolve();
});`;

async function probe(url) {
	const params = new URLSearchParams({
		url,
		proxy_country: PROXY_COUNTRY,
		js_snippet: Buffer.from(jsSnippet).toString('base64'),
		wait_for_selector: 'div.text-xs:nth-child(1)',
	});

	const response = await fetch(`https://scrapingant.p.rapidapi.com/get?${params}`, {
		method: 'GET',
		headers: {
			'x-rapidapi-key': apiKey,
			'x-rapidapi-host': 'scrapingant.p.rapidapi.com',
		},
	});

	const remaining = response.headers.get('x-ratelimit-url-remaining');
	const reset = response.headers.get('x-ratelimit-url-reset');
	if (remaining != null && reset != null) {
		console.error(`ScrapingAnt remaining: ${remaining}, resets at ${new Date(Date.now() + Number(reset) * 1000).toISOString()}`);
	}

	const html = await response.text();
	const match = html.match(/<div id="scraped-prices" data-prices="([^"]+)"/);
	if (!match) {
		throw new Error('Could not locate the scraped price block in the rendered page.');
	}

	return JSON.parse(Buffer.from(match[1], 'base64').toString());
}

const data = await probe(target);
const text = JSON.stringify(data, null, 2);

if (outputPath) {
	await Bun.write(outputPath, text);
	console.error(`Wrote ${outputPath}`);
} else {
	console.log(text);
}
