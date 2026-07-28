import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("Playwright bootstrap declares its CLI provider", async () => {
  const config = JSON.parse(
    await readFile(new URL("../../config.json", import.meta.url), "utf8"),
  );

  assert.deepEqual(config.commands.bootstrap[0].argv, [
    "uv",
    "run",
    "--with",
    "playwright",
    "playwright",
    "install",
    "--with-deps",
    "chromium",
  ]);
});

test("Ticket Agent must run the configured Host checks before committing", async () => {
  const prompt = await readFile(
    new URL("../../prompts/ticket.md", import.meta.url),
    "utf8",
  );

  assert.match(prompt, /\.sandcastle\/config\.json/u);
  assert.match(prompt, /commands\.test/u);
  assert.match(prompt, /commands\.verification/u);
  assert.match(prompt, /全部通过后才能提交/u);
  assert.match(prompt, /不得.*削弱.*验收/u);
});
