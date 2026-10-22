# Roadmap

## Phase 0 — API smoke test
- [x] FastAPI app and local UI
- [x] Project metadata stored in SQLite
- [x] Agnes video submission and `video_id` polling
- [x] Basic API tests and GitHub Actions CI
- [ ] Verify model and request parameters against the user's Agnes account

## Phase 1 — Story and storyboard
- Generate a structured screenplay and shot list
- Validate structured output with Pydantic
- Add human approval before paid video generation
- Track project budgets and maximum shot counts

## Phase 2 — Character bible
- Stable character traits, wardrobe, reference images, voice and exclusions
- Store reference asset IDs where supported by the model
- Separate story canon and episode summaries from transient prompts

## Phase 3 — Multi-shot pipeline
- Durable task queue, per-shot status, retries and idempotency
- Provider adapter interface for additional models

## Phase 4 — Post-production
- Object storage, FFmpeg assembly, voice, subtitles and sound mix
- Quality gates and selective shot regeneration

## Phase 5 — Production hardening
- Authentication, authorization, managed secrets, quotas and spending caps
- Private object storage, signed URLs, observability and backups
