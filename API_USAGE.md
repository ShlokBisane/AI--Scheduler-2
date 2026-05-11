# API Usage & Limits

This file documents recommended API parameters and limits for the project.

## Environment
- API key env var: `OPENAI_API_KEY` (or your provider's key name).
- Recommended config file / env entries: `DEFAULT_TEMPERATURE`, `MAX_TOKENS`, `TOP_P`, `FREQ_PENALTY`, `PRES_PENALTY`.

## Recommended Defaults (project-level)
- `DEFAULT_TEMPERATURE`: 0.2  — low randomness for reliable outputs.
- `TOP_P`: 1.0 — nucleus sampling disabled by default.
- `MAX_TOKENS`: 512 — max tokens for generated responses; adjust per model/context.
- `FREQ_PENALTY`: 0.0 — no frequency penalty by default.
- `PRES_PENALTY`: 0.0 — no presence penalty by default.

Use-case guidance:
- Deterministic responses (summaries, parsing): `temperature` 0.0–0.3.
- Creative responses (brainstorming, copy): `temperature` 0.7–1.0.
- Safety/consistency: keep `temperature` ≤ 0.5.

## Token limits & context
- The total tokens used = prompt tokens + response tokens. Keep the sum below the model's context window.
- For models with ~4k context, avoid sending >3000 prompt tokens if you want a ~1k response.
- For very long contexts use chunking / retrieval + summarization before sending.
- Use a token counting library (e.g., `tiktoken`) to estimate tokens before calls.

## Rate limits, retries, and backoff
- Implement exponential backoff for 429/5xx errors: 3 retries (e.g., 500ms → 1s → 2s), then surface an error.
- Batch requests where supported to reduce per-request overhead.
- Monitor provider rate-limit headers if present and adapt dynamically.

## Cost & performance trade-offs
- Larger `max_tokens` and higher-context calls cost more—trim prompts and use retrieval for long histories.
- Use lower `temperature` and `max_tokens` for high-frequency endpoints.

## Security & data handling
- Never commit `OPENAI_API_KEY` to source control. Keep keys in secure env management or secrets store.
- Redact or avoid sending PII when not necessary.

## Example config snippet (Python)

```python
API_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "max_tokens": 512,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
}
```

## Notes & model-specific limits
- This project uses generic settings; model-specific context windows vary (4k, 8k, 32k+). Always check your chosen model's documentation and adjust `MAX_TOKENS` accordingly.
- If you change models, update `API_USAGE.md` with exact context and token limits for that model.

If you want, I can add per-endpoint examples (chat completion, embeddings), or automatically extract current defaults from `backend/ai_engine.py` and sync them into this file.