import http from "node:http";
import { URL } from "node:url";

const INTERVAL_MS = 1000;
const VALID_SCENARIOS = ["normal", "congestion", "edge"];

function parseArgs() {
  const args = process.argv.slice(2);
  const scenarioFlag = args.indexOf("--scenario");
  const scenario = scenarioFlag !== -1 ? args[scenarioFlag + 1] : "normal";

  if (!VALID_SCENARIOS.includes(scenario)) {
    console.error(`Unknown scenario "${scenario}". Valid: ${VALID_SCENARIOS.join(", ")}`);
    process.exit(1);
  }

  return scenario;
}

function getBackendUrl() {
  return process.env.BACKEND_URL ?? "http://localhost:3000";
}

function postJson(url, body) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const data = JSON.stringify(body, (_, v) =>
      typeof v === "number" && isNaN(v) ? null : v
    );

    const options = {
      hostname: parsed.hostname,
      port: parsed.port || 3000,
      path: parsed.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(data),
      },
    };

    const req = http.request(options, (res) => {
      res.resume();
      resolve(res.statusCode);
    });

    req.on("error", reject);
    req.write(data);
    req.end();
  });
}

async function main() {
  const scenario = parseArgs();
  const backendUrl = getBackendUrl();
  const ingestUrl = `${backendUrl}/api/ingest`;

  const { generateFrame } = await import(`./scenarios/${scenario}.js`);

  let frameCount = 0;

  console.log(`[mock-server] scenario=${scenario}  target=${ingestUrl}`);
  console.log(`[mock-server] posting every ${INTERVAL_MS}ms — Ctrl+C to stop\n`);

  async function tick() {
    frameCount++;

    const result = generateFrame(frameCount);
    const isEdge = scenario === "edge";
    const payload = isEdge ? result.payload : result;
    const label = isEdge ? ` (${result.label})` : "";

    try {
      const status = await postJson(ingestUrl, payload);
      const tag = status >= 400 ? "REJECTED" : "OK";
      console.log(`[frame ${String(frameCount).padStart(5, " ")}] POST → ${status} ${tag}${label}`);
    } catch (err) {
      console.error(`[frame ${String(frameCount).padStart(5, " ")}] POST failed: ${err.message}`);
    }
  }

  // Run first tick immediately, then on interval
  await tick();
  setInterval(tick, INTERVAL_MS);
}

main();
