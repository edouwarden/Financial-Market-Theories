const url = 'https://scrapingant.p.rapidapi.com/get?url=https%3A%2F%2Ffutuur.com%2Fq%2F222373%2Fwill-bitcoin-reach-120k-in-september&proxy_country=JP&response_format=html';
const options = {
	method: 'GET',
	headers: {
		'x-rapidapi-key': process.env.RAPIDAPI_KEY,
		'x-rapidapi-host': 'scrapingant.p.rapidapi.com'
	}
};

try {
	const response = await fetch(url, options);
	const headers = response.headers;
	const limit = headers.get('x-ratelimit-url-limit');
	const remaining = headers.get('x-ratelimit-url-remaining');
	const reset = headers.get('x-ratelimit-url-reset');

	console.log(`limit: ${limit}, remaining: ${remaining}, reset: ${new Date(reset * 1000).toISOString()}`);
	const result = await response.text();
	await Bun.write('result.html', result);
	//<div class="text-xs text-Neutral-4">Price per share .11</div>
	const price = result.match(/<div class="text-xs text-Neutral-4">Price per share (\d+\.\d+)<\/div>/)[1];
	console.log(price);
	//<div class="text-xs text-Neutral-4">Price per share .92</div>
} catch (error) {
	console.error(error);
}
