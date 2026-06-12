import { chromium } from "file:///C:/Users/Leonidas/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/playwright@1.60.0/node_modules/playwright/index.mjs";

const browser = await chromium.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true,
});
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
const response = await page.goto("http://localhost:8501", { waitUntil: "networkidle", timeout: 60000 });
await page.getByRole("button", { name: "CONFERIR JOGOS SALVOS" }).click();
await page.getByText("Jogos salvos aguardando resultado oficial.").waitFor({ timeout: 60000 });

console.log(JSON.stringify({
  httpStatus: response?.status(),
  pendingMessage: await page.getByText("Jogos salvos aguardando resultado oficial.").count(),
  pendingRows: await page.getByText("PENDENTE", { exact: true }).count(),
  pageErrors: [],
}));

await browser.close();
