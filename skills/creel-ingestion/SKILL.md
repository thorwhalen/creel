---
name: creel-ingestion
description: Use when building or changing creel's document ingestion layer — turning raw files (PDF, DOCX, XLSX, HTML, Markdown, images) into Sources the extractors consume. Covers the route-by-format + quality-gate escalation strategy, the structure-preserving local default (Docling), grounding/provenance requirements (page/cell/char-span/bbox), the permissive-license discipline, and when to escalate to OCR/VLM or a multimodal model (Claude native PDF + Citations). Trigger on work in creel/ingest/, file loaders, format handling, OCR, or document parsing. Authoritative source: misc/docs/research/13-document-ingestion.md and decision D-OP7.
metadata:
  audience: developers
---

# creel ingestion (D-OP7)

The ingestion layer (`creel.ingest`) turns raw files into `Source`s. It is upstream
of extraction: **files → (Markdown for the LLM + a structured sidecar carrying
provenance) → extractors**. Authoritative: `misc/docs/research/13-document-ingestion.md`.

## The core principles

1. **No single best parser — route by format + a quality gate.** Escalation ladder:
   cheap local extraction → quality check → OCR/VLM → multimodal model. Don't reach
   for the heavy hammer first.
2. **Default is local, structure-preserving, permissively licensed.** Docling (MIT)
   is the primary default — one dependency gives PDF/DOCX/XLSX/HTML/image parsing
   *with* page+bbox provenance on every element. trafilatura (HTML), openpyxl
   (XLSX), python-docx (DOCX) fill the rest. **License discipline: never depend on
   AGPL/GPL (PyMuPDF4LLM, Marker) in the default `[ingest]` extra** — only as opt-in
   extras with a license warning.
3. **Markdown for the LLM, structured sidecar for everything else.** Emit Markdown
   (token-efficient, LLM-native, preserves headings/lists/tables) *and* a typed
   sidecar (elements + page/cell/char-span/bbox provenance). Don't flatten tables to
   prose — for typed-graph extraction you map cells to nodes/edges, so preserve rows/
   columns (JSON or HTML) with per-cell provenance.
4. **Grounding is mandatory in the data model, optional in the backend.** Every
   produced unit carries a locator; backends that can't supply coordinates
   (markitdown, plain text) populate the coarsest available (page/char span),
   backends that can (Docling, cloud APIs, Claude Citations) populate the finest.
   This is what makes downstream evidence (D8) trustworthy. Selectors live in
   `creel.evidence`: `TextPositionSelector`, `CellSelector`, `PageSelector`,
   `BoundingBoxSelector`, `JsonPathSelector`.

## Decision table (format → default path)

| Format | Default path | Why |
|---|---|---|
| PDF (digital) | Docling → Markdown + sidecar | text layer reliable; ~1000× cheaper than OCR; keeps tables + provenance |
| PDF (scanned) | escalate to VLM OCR (local Surya/Granite-Docling; hosted Mistral OCR/Azure/Google) → multimodal model for visually complex pages | no text layer |
| DOCX | python-docx/mammoth; resolve tracked changes | preserves styles/tables/footnotes |
| XLSX | openpyxl, structured rows + cell-ref provenance, `data_only=True`, handle merged cells | flattening destroys row/col joins |
| HTML | trafilatura main-content → Markdown | strips boilerplate; token-efficient |
| Markdown / text | pass through (normalize encoding) | already LLM-native |
| Image | multimodal model or VLM OCR (deskew/denoise first) | vision required |

## Quality-gate triggers (when to escalate)

- text layer empty OR >~5–10% replacement/garbled chars → OCR;
- merged cells / low table-detection confidence → keep HTML/JSON, not Markdown pipes;
- volume > ~50k pages/mo → prefer local/self-hosted over per-page hosted APIs;
- doc > 100 pages / 32 MB → cannot use Claude-native; chunk or use a local/hosted parser;
- audit-critical values → mandate a coordinate-emitting backend.

## Extras (keep core tiny — D10)

`[ingest]` = docling + trafilatura + openpyxl + python-docx (permissive default).
`[ocr]` = pytesseract (local). `[anthropic]` = Claude native PDF + Citations
grounding provider. Heavier VLM/hosted backends are further opt-in extras. Wrap all
behind one provider-agnostic `Ingestor` interface so creel never hard-depends on a
vendor; expose Claude Citations as one grounding provider among several with a local
char-span/bbox grounder as fallback.

## Claude native document features (build-vs-buy lever)

Claude reads PDFs as text **+** page images (so it sees charts/tables/handwriting);
the **Files API** uploads once and references by id; the **Citations API** returns
exact source references and `cited_text` doesn't count as output tokens (recall
+~15% vs prompt-engineered citations). Limits: 100 pages / 32 MB per request; each
page ≈ 1,500–3,000 tokens + image tokens (expensive at volume). Lean on Claude for
scanned/visually-complex/low-volume docs and free grounding; keep the local layer
for high volume, >100pp docs, offline/air-gapped, and provider independence.
