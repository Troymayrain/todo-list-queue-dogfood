import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  NodeFinalReviewHost,
  NodeIntegrationHost,
} from "../dist/host-boundary.js";

const diagnosticSecret = "diagnostic-[secret].value$";
const failingCommand = [
  process.execPath,
  "-e",
  `process.stdout.write(\`stdout: \${process.argv[1]}\\n\`);
   process.stderr.write(\`stderr: \${process.env.DIAGNOSTIC_SECRET}\\n\`);
   process.exit(7);`,
  diagnosticSecret,
];

function assertSafeCommandDiagnostic(error) {
  assert.equal(error instanceof Error, true);
  assert.match(error.message, /Command: .*<redacted>/u);
  assert.match(error.message, /Exit code: 7/u);
  assert.match(error.message, /stdout: stdout: <redacted>/u);
  assert.match(error.message, /stderr: stderr: <redacted>/u);
  assert.equal(error.message.includes(diagnosticSecret), false);
  assert.equal(error.message.includes("github-secret"), false);
  return true;
}

test("Integration Host reports safe diagnostics for failed project commands", async (t) => {
  const repository = mkdtempSync(join(tmpdir(), "queue-command-diagnostic-"));
  t.after(() => rmSync(repository, { force: true, recursive: true }));
  const environment = {
    ...process.env,
    DIAGNOSTIC_SECRET: diagnosticSecret,
    GITHUB_REPOSITORY: "acme/widget",
    GITHUB_TOKEN: "github-secret",
  };
  const host = new NodeIntegrationHost(repository, environment, {});

  await assert.rejects(
    host.runCommand(failingCommand, environment),
    assertSafeCommandDiagnostic,
  );
});

test("Final Review Host reports safe diagnostics for failed project commands", async (t) => {
  const repository = mkdtempSync(join(tmpdir(), "queue-command-diagnostic-"));
  t.after(() => rmSync(repository, { force: true, recursive: true }));
  const environment = {
    ...process.env,
    DIAGNOSTIC_SECRET: diagnosticSecret,
    GITHUB_REPOSITORY: "acme/widget",
    GITHUB_TOKEN: "github-secret",
  };
  const host = new NodeFinalReviewHost(repository, environment, {});

  await assert.rejects(
    host.runCommand(repository, failingCommand, environment),
    assertSafeCommandDiagnostic,
  );
});
