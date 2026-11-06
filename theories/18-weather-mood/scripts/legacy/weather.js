import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(HERE, '../../results');
const OUT_FILE = join(RESULTS_DIR, 'weather.json');

async function getWeather(place) {
	const url = `https://ai-weather-by-meteosource.p.rapidapi.com/daily?place_id=${place}&language=fr&units=metric`;
	const options = {
		method: 'GET',
		headers: {
			'x-rapidapi-key': process.env.RAPIDAPI_KEY,
			'x-rapidapi-host': 'ai-weather-by-meteosource.p.rapidapi.com'
		}
	};

	try {
		const response = await fetch(url, options);
		const result = await response.json();

		return result;
	} catch (error) {
		console.error(error);
	}
}

export async function weather() {
	const places = ['paris', 'tokyo', 'new-york-city'];
	const report = {
		title: '🌍 Global Weather Report',
		description: '**Current weather conditions in major cities**\n━━━━━━━━━━━━━━━━━━━━━━━',
		places: [],
		source: '• Powered by Meteosource',
		iconUrl: 'https://i.imgur.com/OvMZBs9.png',
		generatedAt: new Date().toISOString()
	};

	for (const place of places) {
		const weather = await getWeather(place);
		if (weather && weather.daily && weather.daily.data && weather.daily.data[0]) {
			const data = weather.daily.data[0];

			// Get weather emoji based on condition

			const weatherIcons = {
				1: '❌',2: '☀️',3: '🌤️',4: '🌤️',5: '☁️',6: '☁️',7: '☁️',8: '☁️',9: '🌫️',
				10: '🌧️',11: '🌧️',12: '🌧️',13: '🌧️',14: '⛈️',15: '⛈️',16: '❄️',17: '❄️',
				18: '❄️',19: '❄️',20: '❄️',21: '❄️',22: '🧊',23: '🧊',24: '🧊',
				25: '🪨',26: '🌙',27: '🌙',28: '🌙',29: '🌙',30: '🌙',31: '🌙',
				32: '🌙🌧️',33: '🌙⛈️',34: '🌙❄️',35: '🌙🧊',36: '🌙🧊',
			};
			const weatherEmoji = weatherIcons[data.icon] || data.weather;
			const city = place.charAt(0).toUpperCase() + place.slice(1);

			report.places.push({
				city,
				place: `${weatherEmoji} ${city}`,
				icon: data.icon,
				emoji: weatherEmoji,
				temperature: data.temperature,
				temperatureMin: data.temperature_min,
				temperatureMax: data.temperature_max,
				humidity: data.humidity,
				wind: data.wind,
				cloudCover: data.cloud_cover,
				summary: data.summary,
				feelsLike: data.feels_like,
				value: `🌡️${data.temperature}°C (*${data.temperature_min}°C/${data.temperature_max}°C*) 💧${data.humidity}% 💨: ${data.wind.speed}m/s ${data.wind.dir} ☁️:${data.cloud_cover}%\n📝Summary: ${data.summary}\nRessenti: ${data.feels_like}°C`
			});
		}
	}

	await mkdir(RESULTS_DIR, { recursive: true });
	await writeFile(OUT_FILE, JSON.stringify(report, null, 2));

	return report;
}

async function main() {
	const report = await weather();
	console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	main().catch((error) => {
		console.error(error);
		process.exitCode = 1;
	});
}
