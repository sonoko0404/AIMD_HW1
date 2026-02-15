# Prompt Kit

## Task 1: Claim–Evidence Extraction

### Prompt A (Baseline)
- prompt content
From the text below, extract five claims about the impact of AI on supply chain performance.
For each claim, provide the supporting evidence from the text.

Text:
[Insert input text here]

- Design rationale
Prompt A serves as a baseline with minimal constraints, allowing the model to freely extract claims and evidence.

### Prompt B (Improved)
- prompt content
You are a careful research assistant.
Your task is to extract claims and supporting evidence from the text below.
Instructions:
1. Output exactly 5 rows in a table with the following columns:
   Claim | Direct evidence snippet | Citation
2. Each claim must be explicitly stated or clearly implied in the text.
3. The evidence snippet must be a verbatim quote copied directly from the text.
4. If a claim is not supported by the text, write “Not supported in this text”.
5. Split the text into chunks of approximately 150–250 words and label them as chunk_1, chunk_2, etc.
6. Use the following citation format: (source_id, chunk_id).

Text (source_id = [SOURCE_ID]):
[Insert input text here]

- Design rationale
Prompt B introduces structured output requirements, explicit citation rules, and a constraint against unsupported claims. This design aims to reduce hallucination, improve grounding, and make the output easier to evaluate across models.
---------------------------------------------------------------------------------------------------------

## Task 2: Cross-source Synthesis

### Prompt A (Baseline)
Compare the two texts below and summarize how they discuss the impact of AI on supply chain performance.
Highlight where they agree and where they disagree.

Text A:
[Insert Text A here]

Text B:
[Insert Text B here]

- Design rationale
Prompt A serves as a baseline with minimal structure. It allows the model to freely compare two sources but does not require explicit citations, structured output, or constraints against unsupported synthesis.

### Prompt B (Improved)
You are a careful research assistant.

Your task is to synthesize findings from two sources about the impact of AI on supply chain performance.

Instructions:
1. Output a table with exactly three columns:
   Agreement | Disagreement | Evidence and citations
2. In the Agreement column, list points where both sources make similar claims.
3. In the Disagreement column, list points where the sources reach different conclusions or emphasize different outcomes.
4. For each agreement or disagreement, clearly state which source supports which position.
5. All evidence must be grounded in the provided texts.
6. If a point is supported by only one source, explicitly state this.
7. If the provided texts do not contain enough information, write “Insufficient evidence in the provided texts”.
8. Split each text into chunks of approximately 150–250 words and label them as chunk_1, chunk_2, etc.
9. Use the following citation format for all evidence: (source_id, chunk_id).

Text A (source_id = [SOURCE_A_ID]):
[Insert Text A here]

Text B (source_id = [SOURCE_B_ID]):
[Insert Text B here]

- Design rationale
Prompt B enforces explicit separation between agreement and disagreement, requires clear attribution to each source, and introduces citation and insufficiency rules. This design aims to reduce unsupported synthesis and make cross-source differences easier to evaluate.