async function fetchBitcoinData() {
	const url = 'https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=15m&limit=96';
	const response = await fetch(url);
	const klines = await response.json();

	return klines.map(k => ({
		time: new Date(parseInt(k[0])),
		open: parseFloat(k[1]),
		high: parseFloat(k[2]),
		low: parseFloat(k[3]),
		close: parseFloat(k[4])
	}));
}

function createChart(candles) {
	const canvas = createCanvas(900, 600);
	const ctx = canvas.getContext('2d');

	// Background
	ctx.fillStyle = '#1a1a1a';
	ctx.fillRect(0, 0, 900, 600);

	// Price range
	const prices = candles.flatMap(c => [c.high, c.low]);
	const minPrice = Math.min(...prices);
	const maxPrice = Math.max(...prices);
	const priceRange = maxPrice - minPrice;

	// Chart area
	const margin = 50;
	const chartWidth = 900;
	const chartHeight = 500;

	// Draw candles
	const candleWidth = 6;
	const spacing = 2;

	candles.forEach((candle, i) => {
		const x = margin + i * (candleWidth + spacing);
		const highY = margin + ((maxPrice - candle.high) / priceRange) * chartHeight;
		const lowY = margin + ((maxPrice - candle.low) / priceRange) * chartHeight;
		const openY = margin + ((maxPrice - candle.open) / priceRange) * chartHeight;
		const closeY = margin + ((maxPrice - candle.close) / priceRange) * chartHeight;

		const isGreen = candle.close > candle.open;
		const color = isGreen ? '#00ff88' : '#ff4444';

		// Wick
		ctx.strokeStyle = '#ccc';
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.moveTo(x + candleWidth / 2, highY);
		ctx.lineTo(x + candleWidth / 2, lowY);
		ctx.stroke();

		// Body
		const bodyTop = Math.min(openY, closeY);
		const bodyHeight = Math.abs(closeY - openY) || 1;

		ctx.fillStyle = color;
		ctx.fillRect(x, bodyTop, candleWidth, bodyHeight);

		ctx.strokeStyle = color;
		ctx.strokeRect(x, bodyTop, candleWidth, bodyHeight);
	});

	// Title
	ctx.fillStyle = '#fff';
	ctx.font = 'bold 20px Arial';
	ctx.textAlign = 'center';
	ctx.fillText('Bitcoin Daily Chart (15min candles)', 350, 30);

	return canvas.toBuffer('image/png');
}

async function main() {
	try {
		console.log('Fetching Bitcoin data...');
		const candles = await fetchBitcoinData();
		console.log(`Got ${candles.length} candles`);

		const chart = createChart(candles);


	} catch (error) {
		console.error('Error:', error.message);
	}
}

main();