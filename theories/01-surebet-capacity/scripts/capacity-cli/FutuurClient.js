const path = require('node:path');

class FutuurClient {
	constructor(DEBUG = false) {
		this.type = 'futuur';
		this.marketsFilePath = path.join(__dirname, '../../data/raw/futuur_markets.json');
		this.markets = [];
		this.baseUrl = 'https://api.futuur.com/api/v1';
		// Futuur does not expose per-size quotes through the public API, so the
		// UI is rendered through ScrapingAnt and the price field is read back.
		this.scrapingAntKey = process.env.RAPIDAPI_KEY || '';
		this.DEBUG = DEBUG;
	}

	getType() {
		return this.type;
	}

	async init() {
		try {
			const marketFile = await Bun.file(this.marketsFilePath);
			if (!(await marketFile.exists()))
				throw new Error('Markets file not found');
			this.markets = await marketFile.json();
			console.log(`Loaded ${this.markets.length} markets from local storage`);
		} catch (error) {
			console.log('No existing markets file found, starting with empty list');
			this.markets = [];
			await this.updateMarkets(2000);
		}
	}

	async saveMarkets() {
		await Bun.write(this.marketsFilePath, JSON.stringify(this.markets, null, 2));
		console.log(`Saved ${this.markets.length} markets`);
	}

	getLatestMarketId() {
		return this.markets.length === 0 ? 0 : Math.max(...this.markets.map(m => m.id));
	}

	async updateMarkets(limit = 200) {
		const newMarkets = [];
		let offset = 0;

		if (this.DEBUG) return;

		while (true) {
			const url = `${this.baseUrl}/markets/?limit=${limit}&offset=${offset}&currency_mode=real_money&ordering=-created_on`;
			const response = await fetch(url);


			if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

			const data = await response.json();
			if (!data.results || data.results.length === 0) break;

			for (const market of data.results)
				newMarkets.push(market);

			if (!data.next) break;
			offset += limit;
		}

		if (newMarkets.length > 0) {
			this._standardize(newMarkets);
			this.markets = newMarkets;
			await this.saveMarkets();
			console.log(`Found ${newMarkets.length} new markets`);
		}

		return newMarkets;
	}

	// Ensure each market has a unified endDate property
	_standardize(marketsArray) {
		try {
			for (const m of marketsArray) {
				m.endDate = m.bet_end_date || m.event_end_date;
				m.closed = m.status === 'closed';
				m.description = m.title;
			}
		} catch (error) {
			console.error('Error standardizing markets:', error);
		}
	
	}

	// Futuur shows "Price per share .12" for a given stake. The regex handles
	// the leading-dot form used by the UI and the ordinary "0.12" form.
	parseFutuurPrice(priceString) {
		if (typeof priceString !== 'string') return null;
		const match = priceString.match(/Price per share\s+([0-9]*\.?[0-9]+)/i)
			|| priceString.match(/([0-9]*\.?[0-9]+)/);
		if (!match) return null;
		const price = Number.parseFloat(match[1]);
		return Number.isFinite(price) && price > 0 && price < 1 ? price : null;
	}

	/**
	 * Convert Futuur's stake curve into incremental ask levels.
	 *
	 * The UI returns, for each stake S, the average price p paid for S/p shares.
	 * Treating each point as an independent level double-counts the shares that
	 * are already included in the next point. The correct local price for the
	 * slice between S[i-1] and S[i] is:
	 *
	 *   (S[i] - S[i-1]) / (S[i]/p[i] - S[i-1]/p[i-1])
	 *
	 * That is the marginal price, which is what an order-book walker needs.
	 */
	formatScrapedPrices(scrapedPrices, orderbook, side) {
		const points = Object.entries(scrapedPrices ?? {})
			.map(([cost, priceString]) => ({
				cost: Number(cost),
				price: this.parseFutuurPrice(priceString),
			}))
			.filter(({ cost, price }) => Number.isFinite(cost) && cost > 0 && price !== null)
			.sort((a, b) => a.cost - b.cost);

		let previousCost = 0;
		let previousShares = 0;
		for (const point of points) {
			const shares = point.cost / point.price;
			const deltaShares = shares - previousShares;
			const deltaCost = point.cost - previousCost;
			if (deltaShares > 1e-9 && deltaCost > 0) {
				const marginalPrice = deltaCost / deltaShares;
				if (marginalPrice > 0 && marginalPrice < 1) {
					orderbook[side].asks.push({ price: marginalPrice, size: deltaShares });
				}
			}
			previousCost = point.cost;
			previousShares = shares;
		}
		orderbook[side].asks.sort((a, b) => a.price - b.price);
	}
	// Convert scraped prices to standardized orderbook format
	formatOrderbook(scrapedPrices) {
		if (!scrapedPrices) return null;
		const orderbook = {
			YES: { bids: [], asks: [], min_order_size: 1 },
			NO: { bids: [], asks: [], min_order_size: 1 }
		};
		if (scrapedPrices.yes) this.formatScrapedPrices(scrapedPrices.yes, orderbook, 'YES');
		if (scrapedPrices.no) this.formatScrapedPrices(scrapedPrices.no, orderbook, 'NO');

		return orderbook;
	}

	async getOrderbook(market) {
		if (!market)
			throw new Error('Market not found');
		const marketUrl = `https://futuur.com/q/${market.id}/${market.slug}`;
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
				for (const size of [1, 5, 10, 50, 100, 250, 500, 1000]) {
					const input = document.querySelector('#place_bet_input');
					if (!input) break;
					input.value = size;
					input.dispatchEvent(new Event('input', {bubbles: true}));
					await sleep(200);
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

		const url = `https://scrapingant.p.rapidapi.com/get?url=${encodeURIComponent(marketUrl)}&proxy_country=${proxy_country}&js_snippet=${js_snippet_param}&wait_for_selector=${wait_for_selector}`;
		const options = {
			method: 'GET',
			headers: {
				'x-rapidapi-key': this.scrapingAntKey,
				'x-rapidapi-host': 'scrapingant.p.rapidapi.com'
			}
		};

		for (let i = 0; i < 2; i++) {
			try {
				const response = await fetch(url, options);
				const result = await response.text();
				const h = response.headers;

				console.log(`Rate limit - remaining: ${h.get('x-ratelimit-url-remaining')}, resets at: ${new Date(Date.now() + Number(h.get('x-ratelimit-url-reset')) * 1000).toISOString()}`);

				const match = result.match(/<div id="scraped-prices" data-prices="([^\"]+)"/);
				if (match) {
					const scrapedPrices = JSON.parse(Buffer.from(match[1], 'base64').toString());
					return this.formatOrderbook(scrapedPrices);
				} else {
					console.log('Could not locate prices in HTML. retry ' + i);
				}
			} catch (error) {
				console.error('Error scraping market prices:', error);
				throw error;
			}
		}
		return null;
	}

	getMarketById(marketId) {
		return this.markets.find(market => market.id === marketId) || null;
	}

	searchMarkets(searchTerm) {
		const term = searchTerm.toLowerCase();
		return this.markets.filter(market =>
			market.question?.toLowerCase().includes(term) ||
			market.title?.toLowerCase().includes(term)
		);
	}

	getMarkets() {
		return this.markets;
	}

	getMarketByPolymarketId(polymarketId) {
		return this.markets.find(market => market.polymarket_id === polymarketId) || null;
	}

	getActiveMarkets() {
		return this.markets.filter(market => market.status === 'active');
	}

	getMarketByUrl(url) {
		const id = url.split('q/')[1].split('/')[0];
		return this.markets.find(market => market.id === parseInt(id)) || null;
	}
}

module.exports = FutuurClient;
