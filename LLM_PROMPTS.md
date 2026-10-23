# LLM Prompt Documentation

## Purpose

This document describes the prompts sent to the language model by `rag_pipeline/pipeline_service.py`. The prompt is used to draft a structured Suspicious Activity Report (SAR) narrative from AML rule results, database enrichment, transaction evidence, and retrieved compliance knowledge.

The prompt is built by `SarRagService._build_prompt_bundle()` and stored with the case for audit and replay.

## When the LLM is called

The LLM is called only when at least one AML rule is triggered. If no rules fire, the service returns `NO_SAR_REQUIRED` and does not perform retrieval or model generation.

The normal flow is:

```text
alert + database enrichment
        -> deterministic AML rules
        -> risk score and evidence blocks
        -> ChromaDB retrieval
        -> system prompt + user prompt
        -> LLM JSON response
        -> parsing and validation
```

## Prompt metadata

The current prompt bundle contains:

| Field | Current value or meaning |
| --- | --- |
| `prompt_version` | `local-fastapi-v6` |
| `model_name` | `HF_MODEL` or `OLLAMA_MODEL`, depending on provider |
| `model_options` | Context size `2048`, temperature `0.2`, top-p `0.9`, and max prediction tokens |
| `prompt_sha256` | SHA-256 of `system_prompt + "\\n---\\n" + user_prompt` |
| `system_prompt` | Stable role, format, safety, and writing rules with dynamic counterparty counts |
| `user_prompt` | Current case facts, triggered rules, evidence IDs, and retrieved reference text |

The prompt hash allows the team to identify the exact prompt version and rendered content used for a generated case.

## System prompt

The following is the template used by the application. Values inside `{braces}` are inserted at runtime.

```text
You are a senior AML compliance analyst drafting a regulator-safe SAR narrative.

CRITICAL: You MUST output STRICT JSON ONLY with this exact structure:
{
    "paragraphs": [
        "Background paragraph...",
        "Transaction Summary paragraph...",
        "Typology paragraph...",
        "Evidence paragraph...",
        "Conclusion paragraph..."
    ],
    "sentences": [
        {"sentence": "First sentence...", "evidence": ["TXN_XXXXX"], "type": "transaction_data"},
        {"sentence": "Second sentence...", "evidence": ["TXN_XXXXX", "TXN_YYYYY"], "type": "transaction_data"}
    ]
}

NON-NEGOTIABLE RULES:
1. EXACTLY 5 paragraphs in `paragraphs`.
2. Each sentence in every paragraph MUST have a corresponding object in `sentences`.
3. Every `evidence` array MUST contain REAL transaction IDs starting with "TXN_" from the evidence buckets below.
4. NEVER use fake evidence like "uae_transfers", "high_velocity_txns", or placeholders like "[E#]".
5. Every suspicious statement MUST follow this pattern: [FACT] + [COMPARISON] + [REASONING].
6. Include reasoning words: "indicating", "suggesting", "consistent with", "demonstrating".
7. NEVER use vague terms: "multiple", "several", "various", "many", "some".
8. NEVER write customer name or ID; always use "the account holder" or "the customer".
9. Use ONLY the exact numbers provided below.
10. CRITICAL: The Conclusion MUST include an explicit filing statement like:
    "Based on the findings, this Suspicious Activity Report (SAR) should be filed with the FIU-IND."

REQUIRED COUNTERPARTY ANALYSIS:
- State exact number: {unique_counterparties} unique counterparties
- State: {prior_counterparties} counterparties had prior relationship
- State: {new_counterparties} counterparties are new
- State: Prior relationship exists: {has_prior_relationship}

If evidence cannot be tied to a real transaction ID, do not invent IDs. Return empty evidence list for that sentence.
```

### What the system prompt controls

- The model role: senior AML compliance analyst.
- JSON-only output rather than free-form prose.
- Exactly five narrative paragraphs.
- Sentence-level evidence objects.
- Real transaction IDs instead of rule bucket names or invented identifiers.
- Fact, comparison, and reasoning structure.
- Required reasoning vocabulary and prohibited vague language.
- PII suppression.
- Exact counterparty analysis.
- Explicit SAR filing language in the conclusion.

The four counterparty values are calculated by database enrichment and inserted into the system prompt. They are not model-generated facts.

## User prompt

The user prompt contains the case-specific facts. Its template is:

```text
Generate SAR narrative JSON using ONLY the data below.

== TRANSACTION DATA ==
- Alert Type: {alert_type}
- Account Type: {account_type}
- Customer Profile: {customer_profile}
- Transaction Count: {transaction_count}
- Total Amount: INR {total_amount}
- Time Window: {time_window_days} days
- Average Amount: INR {average_transaction_amount}
- Velocity: {transactions_per_day} transactions/day (threshold: 5/day)
- Destination Country: {destination_country}

== CUSTOMER FINANCIALS ==
- Declared Monthly Income: INR {declared_monthly_income}
- Avg Monthly Deposits (12m): INR {avg_monthly_deposits_12m}
- Deviation from Baseline: {deviation_from_baseline_pct}%

== COUNTERPARTY INTELLIGENCE ==
- Unique Counterparties: {unique_counterparties}
- Prior Counterparties (12 months): {prior_counterparties}
- New Counterparties: {new_counterparties}
- Has Prior Relationship: {has_prior_relationship}

== TRIGGERED RULES ==
{evidence_summary}

== EVIDENCE BUCKETS (USE THESE EXACT TRANSACTION IDs) ==
- High Velocity Transactions: {high_velocity_transaction_ids}
- UAE Transfers: {uae_transfer_ids}
- Structuring Transactions: {structuring_transaction_ids}

== REFERENCE KNOWLEDGE (Style Only) ==
{retrieved_context}

== CRITICAL INSTRUCTIONS ==
1. Background: Describe the account holder profile using financials. Include exact numbers: income, avg deposits, deviation.
2. Transaction Summary: Reference SPECIFIC transaction IDs like "TXN_00031" in the text, NOT as lists in brackets.
   DO NOT write: [TXN_00031, TXN_00032, ...]
   INSTEAD write: "Transactions such as TXN_00031, TXN_00032, and TXN_00033 demonstrate..."
3. Typology: Identify the AML typology using triggered rules. Reference velocity thresholds and counts.
4. Evidence: Summarize evidence with specific transaction IDs that support findings.
5. Conclusion: MUST include an explicit filing statement: "Based on the findings, this Suspicious Activity Report (SAR) should be filed with the FIU-IND."

Example good sentence with REAL evidence:
"The account received 57 credits totaling INR 14,50,000 in 3 days (FACT), compared to the historical average of 5 credits per month (COMPARISON), indicating abnormal activity (REASONING)." Evidence: ["TXN_00031", "TXN_00032"]

Generate JSON now:
```

The placeholder names above describe the values inserted by the code. The live prompt uses the concrete values from the current alert, enrichment, rules, and retrieval result.

## Dynamic input sources

| Prompt section | Source |
| --- | --- |
| Transaction data | `alert["transactions"]` and normalized transaction details |
| Customer profile | The alert and enrichment output |
| Customer financials | `alert["customer_financials"]`, when available |
| Deviation | Calculated against average monthly deposits over 12 months |
| Counterparty intelligence | `alert["enrichment"]` |
| Triggered rules | `evaluate_rules(alert)` evidence blocks |
| Evidence buckets | Real transaction IDs from alert-window enrichment |
| Reference knowledge | Three ChromaDB retrieval results, each truncated to 1,800 characters |
| Masked identity | The alert passed to prompt building is masked before generation |

The evidence buckets currently include:

- `high_velocity_txns`: alert-window transaction IDs.
- `uae_transfers`: alert-window transaction IDs whose country is `UAE`.
- `structuring_txns`: alert-window transaction IDs below the reporting threshold.

Only the first ten IDs from each bucket are inserted into the prompt. The IDs themselves must come from enrichment data; bucket names are labels and are not valid evidence references.

## Retrieved context rules

The prompt includes up to three documents from the `sar_knowledge` ChromaDB collection. Each document is truncated to `RAG_CHUNK_MAX_CHARS`, currently `1800` characters.

- Typology and guideline documents are passed as compliance context.
- Templates and example narratives are prefixed with `WRITING STYLE REFERENCE ONLY - DO NOT COPY FIGURES`.
- Retrieved examples are writing guidance, not facts about the current customer.
- Case numbers and transaction details must come from the current alert and enrichment data.

## Provider payload

The same two messages are sent to either supported provider.

### Hugging Face

When `LLM_PROVIDER=huggingface`, the service sends a chat-completions request containing:

```json
{
  "model": "<HF_MODEL>",
  "messages": [
    {"role": "system", "content": "<rendered system prompt>"},
    {"role": "user", "content": "<rendered user prompt>"}
  ],
  "temperature": 0.2,
  "top_p": 0.9,
  "max_tokens": 2400,
  "response_format": {"type": "json_object"},
  "reasoning_effort": "low"
}
```

The token is read from `HF_API_TOKEN` and is not part of the prompt bundle.

### Ollama

When `LLM_PROVIDER=ollama`, the service sends:

```python
ollama.chat(
    model=model_name,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    options={
        "num_ctx": 2048,
        "temperature": 0.2,
        "top_p": 0.9,
        "num_predict": 2400,
    },
)
```

If an Ollama GPU error occurs, the service retries with GPU disabled. The prompt content remains the same.

## Expected model response

The model must return JSON with these top-level fields:

```json
{
  "paragraphs": ["...", "...", "...", "...", "..."],
  "sentences": [
    {
      "sentence": "A complete sentence containing relevant evidence.",
      "evidence": ["TXN_00031"],
      "type": "transaction_data"
    }
  ]
}
```

Supported sentence types are:

- `transaction_data`
- `reference_knowledge`
- `evidence_not_available`

The parser normalizes each sentence row to the internal shape `text`, `evidence`, and `type`. It can add a real available transaction ID when a row has empty evidence, but this does not replace final validation.

## Post-generation handling

After the model responds, the service:

1. Extracts the first JSON object from the response.
2. Parses `paragraphs` and `sentences`.
3. Builds five paragraphs from sentence text when structured sentences exist.
4. Adds available transaction evidence when a parsed row is empty.
5. Post-processes the narrative to remove preambles, numbered prefixes, and bracket placeholders.
6. Validates paragraph count, word count, PII, numbers, typology, filing language, evidence IDs, and reasoning language.
7. Builds sentence traceability against fired rules and retrieved documents.

Generation is attempted at most twice. A result is accepted early only when it has at least five structured sentences, sufficient real transaction evidence, and at least 200 narrative words. Final validation remains mandatory.

## Replay and audit

The full `system_prompt` and `user_prompt` are stored in the case prompt payload along with model options and the prompt hash. Replay uses those stored prompts rather than rebuilding them from potentially changed current data.

Audit events record the model name, model options, prompt version, and prompt hash for generation. Secrets such as `HF_API_TOKEN` are not stored in the prompt payload.

## Change checklist for prompt edits

When modifying either prompt:

1. Update `PROMPT_VERSION` in `rag_pipeline/pipeline_service.py`.
2. Update this document with the exact changed instruction.
3. Add or update tests for parsing and validation behavior.
4. Check that all numbers and evidence IDs remain source-bound.
5. Check that the model cannot output raw customer name or ID.
6. Check that replay and prompt hashing still work.
7. Run:

```powershell
pytest tests/test_sar_safety.py -q
pytest tests/test_backend.py -q
```
