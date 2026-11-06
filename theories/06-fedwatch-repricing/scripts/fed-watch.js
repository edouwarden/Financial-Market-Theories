/**
 * CME FedWatch scraper.
 *
 * Returns the current meeting block and target-rate probabilities as plain
 * data. There is no chat or notification layer: run it and pipe the JSON
 * wherever you need it.
 *
 * Compliance: this reads public pages only. It does not log in, bypass a
 * paywall, or solve a bot challenge. Review CME's terms of use and robots.txt
 * before use, keep the request delay conservative, and do not redistribute raw
 * CME data. Prefer CME DataMine or another licensed feed when available.
 *
 * Usage:
 *   FEDWATCH_ACK_TERMS=1 bun fed-watch.js > fedwatch_snapshot.json
 *
 * Environment:
 *   FEDWATCH_USER_AGENT  identifies the client; set a contact address.
 *   FEDWATCH_DELAY_MS    delay between requests, default 2000.
 *   FEDWATCH_ACK_TERMS   must be "1" for the CLI to run.
 */

import { JSDOM } from "jsdom";

const USER_AGENT = process.env.FEDWATCH_USER_AGENT
	|| "financial-market-theories/1.0 (research; set FEDWATCH_USER_AGENT to a contact)";
const DELAY_MS = Number(process.env.FEDWATCH_DELAY_MS || 2000);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const headers = {
	"User-Agent": USER_AGENT,
	"Accept-Language": "en-US,en;q=0.8",
};

/** Serialise requests and wait between them. */
async function politeFetch(url, options = {}) {
	await sleep(Number.isFinite(DELAY_MS) ? DELAY_MS : 2000);
	return fetch(url, options);
}

async function getCurrentFedWatchUrl() {
	const response = await politeFetch("https://www.cmegroup.com/fr/markets/interest-rates/cme-fedwatch-tool.html", { headers });
	if (!response.ok) throw new Error(`CME page returned HTTP ${response.status}`);

	const html = await response.text();
	const iframes = new JSDOM(html).window.document.querySelectorAll("iframe");

	for (const iframe of iframes) {
		if (!iframe.src) continue;

		const iframeUrl = iframe.src.startsWith("/") ? `https://www.cmegroup.com${iframe.src}` : iframe.src;
		const iframeResponse = await politeFetch(iframeUrl, { headers: { ...headers, Referer: response.url } });
		if (!iframeResponse.ok) continue;

		const form = new JSDOM(await iframeResponse.text()).window.document.querySelector("form#Form1, form#form1");
		if (!form) continue;

		const url = new URL(form.action, iframeUrl);
		return url.href.replace("QuikStrikeTools.aspx", "QuikStrikeView.aspx");
	}
	return null;
}

/**
 * Scrape the current FedWatch table.
 *
 * @returns {Promise<{fetchedAt: string, sourceUrl: string, meeting: object|null, probabilities: object[], consensus: object|null}>}
 */
async function scrapeFedWatch() {
	const url = await getCurrentFedWatchUrl();
	if (!url) throw new Error("Could not locate the FedWatch QuikStrike view");

	const response = await politeFetch(url, { headers });
	if (!response.ok) throw new Error(`FedWatch view returned HTTP ${response.status}`);
	const html = await response.text();
	const rows = [...new JSDOM(html).window.document.querySelectorAll("tbody tr")];

	let meeting = null;
	const probabilities = [];

	for (const row of rows) {
		const cells = [...row.querySelectorAll("td")].map((td) => td.textContent.trim());
		if (cells.length === 0) continue;

		if (cells.length > 3 && /^\d{2} \w{3} \d{4}$/.test(cells[0])) {
			meeting = {
				date: cells[0],
				contract: cells[1],
				expires: cells[2],
				midPrice: cells[3],
			};
			continue;
		}

		if (/^\d{3}-\d{3}/.test(cells[0])) {
			probabilities.push({
				targetRateBps: cells[0],
				now: cells[1],
				oneDay: cells[2],
				oneWeek: cells[3],
				oneMonth: cells[4],
			});
		}
	}

	const consensus = probabilities.reduce((best, row) => {
		const probability = Number.parseFloat(String(row.now).replace("%", ""));
		if (!Number.isFinite(probability)) return best;
		return probability > best.probability ? { targetRateBps: row.targetRateBps, probability } : best;
	}, { targetRateBps: null, probability: -1 });

	return {
		fetchedAt: new Date().toISOString(),
		sourceUrl: url,
		meeting,
		probabilities,
		consensus: consensus.targetRateBps ? consensus : null,
	};
}

if (import.meta.main) {
	if (process.env.FEDWATCH_ACK_TERMS !== "1") {
		console.error("Set FEDWATCH_ACK_TERMS=1 after reviewing CME's terms of use and robots.txt.");
		process.exit(1);
	}
	scrapeFedWatch()
		.then((snapshot) => console.log(JSON.stringify(snapshot, null, 2)))
		.catch((error) => {
			console.error(`FedWatch scrape failed: ${error.message}`);
			process.exitCode = 1;
		});
}

export { scrapeFedWatch, getCurrentFedWatchUrl };
