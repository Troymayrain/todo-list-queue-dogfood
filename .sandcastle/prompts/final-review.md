# Final review

Review the temporary merge and return exactly one JSON object with no Markdown or extra text. Use `{"schemaVersion":1,"verdict":"pass","findings":[]}` when no fix is required. Use verdict `needs-fix` only with 1-8 actionable findings. Every finding must contain exactly `path` (repository-relative), `line` (positive integer), `problem` (one line), and `requiredFix` (one line). Do not include secrets, credentials, source excerpts, or speculative findings.
