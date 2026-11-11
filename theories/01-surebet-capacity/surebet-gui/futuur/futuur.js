const crypto = require('crypto');

const PRIVATE_KEY = process.env.FUTUUR_PRIVATE_KEY;
const PUBLIC_KEY = process.env.FUTUUR_PUBLIC_KEY;
const BASE_URL = 'https://api.futuur.com/api/v1/';

// Check if environment variables are set
if (!PRIVATE_KEY || !PUBLIC_KEY) {
	console.error('Error: FUTUUR_PRIVATE_KEY and FUTUUR_PUBLIC_KEY environment variables must be set');
	console.log('Set them with:');
	console.log('export FUTUUR_PRIVATE_KEY="your_private_key"');
	console.log('export FUTUUR_PUBLIC_KEY="your_public_key"');
	process.exit(1);
}

function buildSignature(queryParams) {
	const timestamp = Math.floor(Date.now() / 1000);

	// According to documentation: "full raw headers, POST, and GET data ordered alphabetically"
	// Include Key and Timestamp in the parameters to sign
	const allParams = {
		...queryParams,
		'Key': PUBLIC_KEY,
		'Timestamp': timestamp
	};

	// Sort parameters by key alphabetically
	const sortedParams = Object.keys(allParams)
		.sort()
		.reduce((result, key) => {
			result[key] = allParams[key];
			return result;
		}, {});

	// Create query string exactly as per documentation example
	const queryString = new URLSearchParams(sortedParams).toString();
	console.log('Query string for signature:', queryString);

	// Create HMAC signature
	const hmac = crypto.createHmac('sha512', PRIVATE_KEY);
	hmac.update(queryString);
	const signature = hmac.digest('hex');

	console.log('Generated signature:', signature);

	return {
		hmac: signature,
		Timestamp: timestamp
	};
}

function buildHeaders(queryParams) {
	const signature = buildSignature(queryParams);

	// Try basic header format first
	const headers = {
		'Key': PUBLIC_KEY,
		'Timestamp': signature.Timestamp.toString(),
		'HMAC': signature.hmac
	};
	console.log('Headers:', headers);
	return headers;
}

async function getOrderBook(currency, currencyMode, outcome, question, status = 'open', user) {
	// Query parameters for the request
	const queryParams = {
		currency: currency,
		currency_mode: currencyMode,
		outcome: outcome,
		question: question,
		status: status,
		user: user
	};

	const headers = buildHeaders(queryParams);

	try {
		const queryString = new URLSearchParams(queryParams).toString();
		const url = `${BASE_URL}orders/book/?${queryString}`;
		console.log('Request URL:', url);

		const response = await fetch(url, {
			method: 'GET',
			headers: {
				...headers,
				'Content-Type': 'application/json'
			}
		});

		console.log('Response status:', response.status);
		console.log('Response headers:', Object.fromEntries(response.headers.entries()));

		if (!response.ok) {
			const errorText = await response.text();
			console.error('Error response body:', errorText);
			throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
		}

		const data = await response.json();
		return data;
	} catch (error) {
		console.error('Error fetching order book:', error);
		throw error;
	}
}

// Example usage
async function main() {
	try {
		// Example parameters - replace with your actual values
		const orderBook = await getOrderBook(
			'USD',           // currency
			'real_money',    // currency_mode
			1,               // outcome
			1,               // question
			'open',          // status
			1                // user
		);

		console.log('Order Book:', JSON.stringify(orderBook, null, 2));
	} catch (error) {
		console.error('Failed to fetch order book:', error);
	}
}

// Uncomment to run the example
main();
