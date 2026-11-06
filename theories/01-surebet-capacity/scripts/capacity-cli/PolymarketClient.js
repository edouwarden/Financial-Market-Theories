const path = require('node:path');

class PolymarketClient {

	constructor(DEBUG = false) {
		this.type = 'polymarket';
		this.marketsFilePath = path.join(__dirname, '../../data/raw/polymarket_markets.json');
		this.markets = [];
		this.baseUrl = 'https://gamma-api.polymarket.com';
		this.clobBaseUrl = 'https://clob.polymarket.com';
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
			await this.updateMarkets(250);
		}
	}

	async saveMarkets() {
		await Bun.write(this.marketsFilePath, JSON.stringify(this.markets, null, 2));
		console.log(`Saved ${this.markets.length} markets`);
	}

	getLatestMarketId() {
		return this.markets.length === 0 ? 0 : Math.max(...this.markets.map(m => parseInt(m.id)));
	}

	async updateMarkets(limit = 100) {
		const newMarkets = [];
		let offset = 0;

		if (this.DEBUG) return;

		while (true) {
			const response = await fetch(
				`${this.baseUrl}/markets?closed=false&limit=${limit}&offset=${offset}&order=id&ascending=false`
			);
			//console.log(response);
			if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

			const data = await response.json();
			//if( offset/limit  == 5)
			//	console.log(data);
			if (data.length === 0) break;

			for (const market of data) 
				newMarkets.push(market);
			

			if (offset > 10000) break;
			offset += limit;
			await Bun.sleep(500);
			console.log(`Fetched ${offset / limit} pages`);
		}

		if (newMarkets.length > 0) {
			this._standardize(newMarkets);
			this.markets = newMarkets;
			await this.saveMarkets();
			console.log(`Found ${newMarkets.length} new markets`);
		}

		return newMarkets;
	}

	// Convert Polymarket orderbook to standardized format
	formatOrderbook(rawOrderbooks, outcomes) {
		const standardizedOrderbook = {};

		for (let i = 0; i < outcomes.length; i++) {
			const outcome = outcomes[i];
			const standardizedOutcome = outcome.toUpperCase(); // Normalize to uppercase

			if (rawOrderbooks[outcome]) {
				const raw = rawOrderbooks[outcome];
				standardizedOrderbook[standardizedOutcome] = {
					bids: raw.bids ? raw.bids.map(bid => ({
						price: parseFloat(bid.price),
						size: parseFloat(bid.size)
					})) : [],
					asks: raw.asks ? raw.asks.map(ask => ({
						price: parseFloat(ask.price),
						size: parseFloat(ask.size)
					})) : [],
					min_order_size: raw.min_order_size || 1
				};

				// Sort bids by price (descending - highest first)
				standardizedOrderbook[standardizedOutcome].bids.sort((a, b) => b.price - a.price);
				// Sort asks by price (ascending - lowest first)
				standardizedOrderbook[standardizedOutcome].asks.sort((a, b) => a.price - b.price);
			}
		}

		return standardizedOrderbook;
	}

	async getOrderbook(market) {
		try {
			const tokenIds = JSON.parse(market.clobTokenIds);
			const outcomes = JSON.parse(market.outcomes);
			const rawOrderbooks = {};

			for (let i = 0; i < tokenIds.length; i++) {
				const token = tokenIds[i];
				if (token.length < 20) continue;
				try {
					const response = await fetch(`${this.clobBaseUrl}/book?token_id=${token}`);
					if (response.ok) {
						const orderbook = await response.json();
						rawOrderbooks[outcomes[i]] = {
							bids: orderbook.bids,
							asks: orderbook.asks,
							min_order_size: orderbook.min_order_size
						};
					}
				} catch (error) {
					console.warn(`Failed to fetch orderbook for ${outcomes[i]}`);
				}
			}

			return this.formatOrderbook(rawOrderbooks, outcomes);
		} catch (error) {
			console.warn('Error parsing market data:', error);
			return {};
		}
	}

	getMarkets() {
		return this.markets;
	}

	getMarketById(marketId) {
		return this.markets.find(market => market.id === marketId) || null;
	}

	getMarketBySlug(slug) {
		return this.markets.find(market => market.slug === slug) || null;
	}

	getMarketByUrl(url, outcome) {
		const eventSlug = url.split('/').pop();
		const found = this.markets.filter(market => market.events[0].slug == eventSlug);
		const outcomeFound = found.find(market => market.slug.includes(outcome.toLowerCase()));
		return outcomeFound || null;
	}

	searchMarkets(searchTerm) {
		return this.markets.filter(m => m.question.toLowerCase().includes(searchTerm.toLowerCase()));
	}

	_standardize(marketsArray) {
		try {
			for (const m of marketsArray) {
				m.endDate = m.endDateIso;
				m.id = parseInt(m.id);
			}
		} catch (error) {
			console.error('Error standardizing markets:', error);
		}
	}
}

module.exports = PolymarketClient;
