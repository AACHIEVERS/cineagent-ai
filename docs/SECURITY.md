# Security baseline

1. `AGNES_API_KEY` is read only by the backend. Never expose it to browser JavaScript.
2. Keep `.env` out of Git; commit only a blank `.env.example`.
3. Use managed secrets and rotate keys in production.
4. Add authentication and authorization before exposing project APIs publicly.
5. Apply request limits, rate limits, per-user budgets and provider concurrency limits.
6. Do not log Authorization headers, API keys or full private prompts by default.
7. Store generated files in private object storage and use expiring signed URLs.
8. Validate model output; never execute generated code.
9. Use bounded retries with backoff; avoid tight polling loops.
10. Confirm provider terms, parameters, quotas and pricing before production.
