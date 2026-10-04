# Verification scripts

One script per task: `scripts/verify/T-xxx.py`, `.sh`, or `.spec.ts` (Playwright).
Run with: `python3 scripts/verify/run.py T-xxx`. The runner writes the log and the row in docs/VERIFICATION.md.

Rules for a good verification script:
- Assert results. Exit non-zero on any failure. Printing is not testing.
- Cover every acceptance criterion for the task in docs/TESTING.md.
- Include at least one negative case (bad input, missing dependency, over the retry cap).
- Use real tools for the layer: pytest, httpx or curl for APIs, psql for DB, Playwright for UI, Newman for Postman collections.
- Clean up what it creates (test tickets, test rows).
- Never print secrets.
