

async function scrapFutuurEvent (futuurURL)
{
  const js_snippet = `return new Promise(async resolve => {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    const getPrice = () => document.querySelector('div.text-xs:nth-child(1)')?.textContent?.trim() || '';
    const prices = { yes: {}, no: {} };

    for (const side of ['yes', 'no']) {
      if (side === 'no') {
        Array.from(document.querySelectorAll('button'))
          .find(b => b.querySelector('span.text-lg.font-medium')?.textContent?.trim() === 'No')?.click();
        await sleep(500);
      }
      for (const size of [1, 5, 10, 50]) {
        const input = document.querySelector('#place_bet_input');
        if (!input) break;
        input.value = size;
        input.dispatchEvent(new Event('input', {bubbles: true}));
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

  const js_snippet_base64 = Buffer.from(js_snippet).toString('base64');
  const js_snippet_param = encodeURIComponent(js_snippet_base64);
  const wait_for_selector = 'div.text-xs:nth-child(1)';
  const proxy_country = 'JP';

  const url = `https://scrapingant.p.rapidapi.com/get?url=${target}&proxy_country=${proxy_country}&js_snippet=${js_snippet_param}&wait_for_selector=${wait_for_selector}`;
  const options = { method: 'GET', headers: { 'x-rapidapi-key': process.env.RAPIDAPI_KEY, 'x-rapidapi-host': 'scrapingant.p.rapidapi.com' } };

  try {
    const response = await fetch(url, options);
    const result = await response.text();
    const h = response.headers;

    console.log(`limit: ${h.get('x-ratelimit-url-limit')}, remaining: ${h.get('x-ratelimit-url-remaining')}, resets_at: ${new Date(Date.now() + Number(h.get('x-ratelimit-url-reset')) * 1000).toISOString()}`);

    const match = result.match(/<div id="scraped-prices" data-prices="([^\"]+)"/);
    if (match) {
      try {
        console.log('Prices per share by bet size:', JSON.parse(Buffer.from(match[1], 'base64').toString()));
        return JSON.parse(Buffer.from(match[1], 'base64').toString());
      } catch (e) {
        console.error('Failed to parse prices', e);
      }
    } else {
      await Bun.write('result6.html', result);
      console.log('Could not locate prices in HTML.');
    }
  } catch (error) {
      console.error(error);
  }
}
const target = 'https://futuur.com/q/222373/will-bitcoin-reach-120k-in-september';
(async () => {
  const data = await scrapFutuurEvent(target);
  await Bun.write('futuur_event.json', JSON.stringify(data, null, 2));
  /*{
    yes: {
      "1": "Price per share .04",
      "5": "Price per share .05",
      "10": "Price per share .06",
      "50": "Price per share .11",
    },
    no: {
      "1": "Price per share .97",
      "5": "Price per share .97",
      "10": "Price per share .97",
      "50": "Price per share .97",
    },
  }*/
})();

async function getFullFutuurMarkets() {
	let url = 'https://api.futuur.com/api/v1/markets/?limit=200&offset=0&currency_mode=real_money&ordering=created_on'
	let markets = [];
	let response = await fetch('https://api.futuur.com/api/v1/markets/?limit=200&offset=0&currency_mode=real_money&ordering=created_on')
	if (!response.ok)
		throw new Error(`HTTP error! status: ${response.status}`);

	let data = await response.json();
	markets = data.results;
	while (response.ok && response.pagination.next) {
		url = response.pagination.next;
		response = await fetch(url);
		if (!response.ok)
			throw new Error(`HTTP error! status: ${response.status}`);

		data = await response.json();
		markets = markets.concat(data.results);
	}

	return markets;
}

async function getNewFutuurMarkets(fullmarkets) {
	let newMarkets = [];
	let count = -1;
	let offset = 0;
	const size = 20;
	while (count == size || count == -1) {
		const response = await fetch('https://api.futuur.com/api/v1/markets/?limit=' + size + '&offset=' + offset + '&currency_mode=real_money&ordering=created_on')
		if (!response.ok)
			throw new Error(`HTTP error! status: ${response.status}`);

		let data = await response.json();
		let fetchedNewMarkets = data.results.filter(market => !fullmarkets.find(fullmarket => fullmarket.id === market.id));
		newMarkets = newMarkets.concat(fetchedNewMarkets);
		count = fetchedNewMarkets.length;
		offset += size;
	}

	return newMarkets;
}
