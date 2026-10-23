# Member 3: AI, AML Rules, RAG, and Safety

## Role

Own the intelligence layer that detects suspicious patterns and drafts explainable SAR narratives. This member is responsible for deterministic AML rules, retrieval, model prompting, parsing, validation, evidence traceability, and the compliance knowledge corpus.

## Primary files

- `rag_pipeline/rule_engine.py` - YAML rule loading, condition evaluation, evidence blocks, risk score, and retrieval query construction.
- `rag_pipeline/pipeline_service.py` - masking, retrieval, prompt construction, model call, parsing, validation, and sentence traceability.
- `rag_pipeline/ingestion_pipeline.py` - corpus chunking, metadata, embeddings, and ChromaDB ingestion.
- `rag_pipeline/sar_rag_pipeline.py` - pipeline support or compatibility code.
- `sar_safety.py` - standalone safety checks and retry/audit utilities.
- `rules.yaml` - active AML rules and thresholds.
- `data/aml_typologies.txt`, `data/regulatory_writing_guidelines.txt`, `data/sar_narrative_templates.txt`, and `data/example_sar_narratives.txt` - retrieval corpus.
- `tests/test_sar_safety.py` and AI-focused tests added under `tests/`.

## Main responsibilities

1. Keep rule decisions deterministic, inspectable, and driven by `rules.yaml`.
2. Add or modify rules with explicit conditions, thresholds, confidence, observations, and regulation references.
3. Build retrieval queries from case facts and store retrieval metadata for replay and audit.
4. Mask PII before retrieval and generation.
5. Maintain the strict structured output contract: narrative text plus sentence objects containing `text`, `evidence`, and `type`.
6. Validate paragraph count, word count, PII, placeholders, typology, numbers, filing language, evidence IDs, and reasoning language.
7. Ensure every sentence evidence reference is a real transaction ID when transaction evidence is required.
8. Keep retries bounded and observable; never loop indefinitely on model failure.
9. Prevent examples retrieved from the corpus from being mistaken for facts about the current customer.

## AI pipeline contract

```text
enriched alert -> AML evidence -> masked alert -> retrieval -> prompt/model
               -> structured parse -> safety validation -> sentence traceability
```

The model is not the source of truth for amounts, dates, customer facts, or transaction IDs. Those values must come from the alert, database enrichment, fired rules, or explicitly labeled reference knowledge.

## Evidence contract

The output should follow this shape:

```json
{
  "text": "The account received 57 credits in 3 days, indicating abnormal activity.",
  "evidence": ["TXN_00031", "TXN_00032"],
  "type": "transaction_data"
}
```

Valid types are `transaction_data`, `reference_knowledge`, and `evidence_not_available`. Unknown or fabricated transaction IDs must fail validation. Vague terms such as `multiple`, `several`, `various`, or `many` should be rejected when they replace measurable evidence.

## Example rule contribution

Add configuration before code whenever the behavior is a normal AML threshold rule:

```yaml
- id: AML-014
  name: Unusual Transaction Frequency
  confidence: 0.82
  conditions:
    - field: derived.txn_per_day
      operator: gt
      value: 10
  observation: "Transaction frequency exceeds the configured daily threshold"
  regulation: "Internal AML monitoring standard"
```

Then add a rule-engine test for a matching case, a non-matching case, and the generated evidence block. Keep field paths and operators consistent with the existing engine.

## Safety and privacy checklist

- Mask customer name and customer ID before the model call.
- Reject raw customer name or ID in generated narrative text.
- Reject unsupported placeholders and copied example figures.
- Require exact evidence IDs from the supplied evidence pack.
- Store prompt/model/retrieval metadata needed for replay, without logging secrets.
- Treat a failed validation as a failed generation, not as an approval candidate.

## Testing responsibilities

Run the focused safety tests and the full suite when changing shared pipeline behavior:

```powershell
pytest tests/test_sar_safety.py -q
pytest -q
```

Add tests for changed rules, masking, malformed model JSON, retry behavior, fake evidence IDs, missing evidence, PII leakage, unsupported numbers, and validation failures. Tests should use deterministic fixtures and avoid requiring a live model when the behavior can be tested at the parser or validator boundary.

## Handoff with other members

- **Backend member:** provide a stable service result containing risk, evidence, narrative, validation, retrieval metadata, and failure details.
- **Database member:** consume enriched transaction objects and explain which fields are required; never query PostgreSQL from the model layer unless the existing boundary explicitly permits it.
- **Frontend member:** document sentence types, evidence ID format, validation fields, and retry/error states.

## Definition of done

- The change has a deterministic test.
- New model output fields are schema-validated and backwards compatible where possible.
- PII and evidence validation still pass.
- Replay metadata remains sufficient to understand the result.
- The change does not turn reference text or model guesses into case facts.
