import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("Playwright browser installation declares its CLI provider", async () => {
  const config = JSON.parse(
    await readFile(new URL("../../config.json", import.meta.url), "utf8"),
  );

  assert.deepEqual(config.commands.test[0].argv, [
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
