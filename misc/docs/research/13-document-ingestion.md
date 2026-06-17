# Document Ingestion & Normalization for LLM-Based Information Extraction: A 2026 Best-Practices Report

**Author: Thor Whalen**
**Date: June 17, 2026**

> *Note: This report is structured to be saved directly as a Markdown (`.md`) file — e.g., `document-ingestion-normalization-2026.md`.*

## TL;DR

- **Default to fast, local, structure-preserving text extraction (PyMuPDF4LLM / Docling) and only escalate to heavier OCR or a multimodal model when the cheap path fails a quality gate.** For a typed-graph extraction library, the ingestion layer should emit a normalized, layout-aware representation (Markdown for the LLM + a structured sidecar carrying page/cell/char-span provenance), not a flat blob of text.
- **Feed raw files directly to a multimodal model (e.g., Claude) when documents are scanned, visually complex, or low-volume; pre-parse with deterministic tools when documents are digital-native, high-volume, or you need cheap, repeatable, grounded output.** Claude's native PDF + Citations features are a strong build-vs-buy lever for grounding, but the 100-page/32 MB limits and per-page image-token cost make them a complement to, not a replacement for, a local parsing layer.
- **Grounding/provenance must be a first-class concern: every extracted node and edge should trace back to a page number, cell reference, character span, or bounding box.** Tools that emit coordinates (Docling, Azure/Google/Textract, Reducto, Surya, Chunkr) or the Claude Citations API enable verification and hallucination control; tools that only emit prose (markitdown, plain Tesseract) do not.

## Key Findings

1. **There is no single best parser; the right path is format- and goal-dependent.** The decisive variables are: is the file digital-native or scanned, how structurally complex is it (multi-column, tables, merged cells), what volume, and how much do you need grounding. A typed-graph use case raises the bar on grounding and on table fidelity specifically.

2. **The open-source landscape matured dramatically in 2024–2026.** Docling (MIT) and PyMuPDF4LLM (AGPL/commercial) are the strongest embeddable Python defaults; a wave of VLM OCR models reached state-of-the-art quality in late 2025 — olmOCR 2 (olmOCR-2-7B-1025) scored 82.4 on olmOCR-Bench, outperforming specialized tools such as Marker (76.1) and MinerU (75.8), per Ai2's October 2025 release. Hosted parsers (Mistral OCR 3, LlamaParse, Reducto, Azure/Google/AWS) compete on accuracy, provenance, and enterprise features — with Mistral OCR 3 (Dec 2025) collapsing the price floor to $1–2 per 1,000 pages.

3. **Structured table parsing beats prose flattening whenever downstream consumers query by row/column/cell or build typed records** — which is exactly the typed-graph case. Flattening a table to prose destroys the row–column relationships the graph extractor needs and creates ambiguity and hallucination risk.

4. **Licensing is a first-order design constraint for an embeddable OSS library.** Docling (MIT), Surya/markitdown/unstructured/trafilatura (Apache-2.0/MIT) are safe to depend on; PyMuPDF4LLM and Marker carry AGPL/GPL + commercial dual licensing that can be a non-starter for permissively licensed downstream products. Hosted APIs avoid the license issue but introduce a network dependency, cost, and data-egress considerations.

5. **Claude's native document features (PDF text+vision, Files API, Citations) meaningfully shift build-vs-buy** for grounding, but should be wrapped behind a provider-agnostic interface so the library is not locked to one vendor.

## Details

### (1) Convert vs. process natively vs. feed-the-file-to-the-model

There are three ingestion strategies, and a mature library should support all three behind one interface.

**A. Convert to a common format (Markdown/text) up front.** The dominant pattern for RAG and extraction. Markdown is the sweet spot: every major LLM was trained on enormous quantities of it, it is token-efficient (heading/list syntax adds ~1% overhead), and it preserves the structural cues (headings, lists, fenced code, pipe tables) the model uses to reason. Plain text is acceptable only for genuinely prose-only content (transcripts, email bodies); it strips every structural cue and forces the model to infer structure from sentence patterns, which "works for short documents and breaks on long ones."

- *Pros:* cheapest at scale (no per-page image tokens), deterministic, debuggable, cacheable, provider-agnostic, full control over chunking and reading order.
- *Cons:* the conversion step can silently corrupt structure (tables flatten, footnotes detach, reading order scrambles in multi-column layouts); requires you to own/maintain the parsing layer; OCR errors propagate downstream.
- *Failure modes:* scanned/image-only PDFs (no text layer → empty output unless OCR is triggered); custom font encodings without a CMAP produce garbled or U+FFFD-laden text; complex tables collapse.

**B. Process natively per format.** Use format-aware libraries (openpyxl for XLSX, python-docx/mammoth for DOCX, trafilatura for HTML) to extract typed structures directly rather than flattening to a generic text stream. Highest fidelity for structured formats — you keep cell coordinates, formulas, sheet names, tracked-changes state — at the cost of more code paths to maintain.

**C. Feed the raw file to a multimodal model.** Send the PDF/image directly to a vision-capable LLM (Claude, Gemini, GPT) and let it read text + visual content in one shot. Anthropic's PDF support converts each page to an image *and* extracts text, so the model sees charts, tables, stamps, and handwriting that text extraction misses.

- *When feeding raw beats pre-parsing:* scanned/photographed documents; visually complex pages (charts, diagrams, dense financial tables, forms with checkboxes); low-to-moderate volume where per-page token cost is acceptable; when you want to skip building/maintaining a parser; when you need the model to reason over layout it would lose in flattening.
- *When pre-parsing beats raw:* high volume (image tokens are expensive — each PDF page costs roughly 1,500–3,000 text tokens plus image tokens, and dense PDFs can exhaust the context window before the page limit); digital-native documents where text extraction is near-perfect and ~1,000× cheaper than OCR; when you need deterministic, reproducible output; when documents exceed the model's page/size limits.

Anthropic's own guidance: each PDF page "typically uses 1,500-3,000 tokens per page depending on content density," and "since each page is converted into an image, the same image-based cost calculations are applied." Dense PDFs "can fill the context window before reaching the page limit."

**Trade-off summary across the seven axes:**

| Axis | Convert to MD/text | Native per-format parse | Feed raw to multimodal model |
|---|---|---|---|
| Accuracy (digital-native) | High | Highest for structured formats | High but probabilistic |
| Accuracy (scanned/visual) | Low without OCR | N/A | Highest |
| Cost (tokens) | Lowest | Lowest | Highest (image tokens/page) |
| Latency | Low | Low | Higher (per-page vision) |
| Control over parsing | High | Highest | Lowest |
| Grounding/citation | Tool-dependent | Native (cell/char) | Citations API (page/char) |
| Maintainability | Medium (you own it) | Low (many code paths) | Highest (vendor owns it) |

### (2) Per-format pitfalls

**PDF.** The hardest format. Multi-column layouts break naive left-to-right text extraction (reading order scrambles); tables flatten into prose losing row/column structure; scanned/image-only PDFs have no text layer and require OCR; headers/footers/page numbers leak into the body; footnotes detach from their anchors. A robust pipeline detects whether a page has a usable text layer and only invokes OCR where needed — PyMuPDF4LLM does this automatically (OCR is "roughly 1,000× slower than native text extraction," and applying full-page OCR over already-clean text "can actually degrade output quality"). It also detects garbled text (high U+FFFD rates from copy-protected/bad-CMAP fonts) as an OCR trigger.

**XLSX.** Spreadsheets are deceptively hard. Multiple sheets must each be enumerated. **Merged cells** are the classic trap: in the OOXML model (and openpyxl), merging does not create one big cell — it *hides* the non-top-left cells, which become `MergeCells` with value `None`. Naïvely reading gives you one value and a cluster of blanks, destroying multi-row/multi-column headers. **Formulas vs. values:** openpyxl returns the formula string by default; you must pass `data_only=True` to get the last-cached computed value (and if the file was never opened in Excel, even that may be absent). **Hidden rows/columns** may be intentional (scratch calculations) and pollute extraction. **Type inference** (dates, currency, percentages stored as floats with number-format metadata) requires reading the cell format, not just the value.

**DOCX.** **Tracked changes** mean the visible text depends on whether you read insertions/deletions — extracting raw XML can yield both the "before" and "after" text concatenated. **Embedded objects** (charts, OLE, images) are not text and need separate handling. **Styles** carry the heading hierarchy; lose them and you lose document structure. **Tables and footnotes** live in separate XML parts and are easy to drop. Anthropic's own recommendation for DOCX with images: "convert them to PDF format first, then use PDF support to take advantage of the built-in image parsing" and citations.

**HTML.** The dominant problem is **boilerplate**: nav bars, ads, cookie banners, sidebars, footers. Main-content extraction (a.k.a. boilerplate removal, DOM-based content extraction) is a solved-ish problem: trafilatura is the strongest open-source option, scoring a mean F1 of 0.937 (mean precision 0.978, recall 0.92) in OSTI's independent evaluation "An Evaluation of Main Content Extraction Libraries," ahead of readability-lxml and newspaper. Convert the cleaned HTML to Markdown before the LLM — strip scripts/styling, then run through a converter so "the LLM sees structured prose instead of tag soup," cutting tokens and improving accuracy. Preserve semantic structure (headings, lists, tables) during conversion.

**Scanned images.** OCR engine quality varies widely. Tesseract is "still viable for clean, single-column printed text on CPU-constrained devices, but it struggles with layouts, tables, and low-contrast scans." Modern VLM OCR (Surya, dots.ocr, DeepSeek-OCR, Mistral OCR) significantly outperforms on complex layouts. **Handwriting** is the hardest case: per Mistral's internal benchmark (reported by PyImageSearch, Dec 2025), OCR 3 "achieves an 88.9% accuracy rate on handwriting compared to Azure's 78.2%, and 96.6% on tables versus Textract's 84.8%"; general-purpose open models still struggle (DeepSeek scored 57.2 on a multilingual handwriting comparison). Pre-processing (deskew, binarize, denoise) materially improves classic-OCR accuracy.

### (3) When structured parsing beats prose flattening

The evidence is nuanced but points clearly for the typed-graph case. For *retrieval/QA* over tables, Markdown table representation has measured higher than HTML in some GPT evaluations (≈60.7% vs 53.6%) because the simpler syntax reduces structural ambiguity. But for **complex tables with merged cells, multi-row headers, and colspan/rowspan**, HTML (or a true structured representation) wins decisively: in the TableEval benchmark, models scored ~2 points higher F1 on HTML/LaTeX than Markdown overall, with GPT-4o showing a 22% F1 jump on table-structure understanding and roughly **2× better merged-cell detection** on HTML. This is why Mistral OCR 3 emits Markdown with **HTML-based table reconstruction** (colspan/rowspan) for complex tables.

For **typed-graph extraction specifically**, the calculus is different from RAG. You are not asking the model to "read around" a table — you are mapping cells to typed nodes and edges. Preserving the table as structured rows/columns matters whenever:
- A value's meaning depends on its row header *and* column header (e.g., "2023 / Total liabilities" → a typed `FinancialMetric` node with `year=2023`).
- You need to emit one record per row (line-item invoices, holdings tables, lab results).
- Cells must be individually grounded back to a coordinate for verification.

Flatten such a table to prose and you get convolution at table/text boundaries (the last table row "can blend easily with the next line"), loss of the row–column join key, and a higher hallucination rate. **Recommendation:** for the typed-graph pipeline, preserve tables as structured rows/columns (JSON or HTML) with per-cell provenance, and reserve prose flattening for genuinely narrative content.

### (4) The tooling landscape (maturity, license, recency, Python-friendliness)

**Open-source, embeddable in Python:**

- **Docling (IBM)** — *Best overall OSS default for a typed-graph library.* MIT-licensed code (hosted in the LF AI & Data Foundation), Apache-2.0 model weights. Parses PDF, DOCX, PPTX, XLSX, HTML, images, audio into a unified **`DoclingDocument`** Pydantic model that carries text, tables, layout (bounding boxes), reading order, and **provenance (page numbers + bbox) on every node via `DocItem.prov`**. TableFormer handles complex tables (merged cells, hierarchical headers); the optional Granite-Docling-258M VLM (Apache 2.0, released Sept 17, 2025) does one-shot conversion. Very active (100+ releases since the Aug 2025 PyPI release; the Heron layout model landed Dec 2025). Python 3.10+. Exports Markdown/HTML/JSON/DocTags. This is the strongest combination of permissive license, provenance, and structure for an OSS library.
- **PyMuPDF4LLM (Artifex)** — *Best lightweight, fast, local default for PDFs.* One-line `to_markdown()`, layout-aware, multi-column reading order, table detection to Markdown, automatic hybrid OCR (only where needed), page-chunking with metadata, `to_json()` with bounding boxes. No GPU/cloud. **License caveat: AGPL-3.0 or commercial from Artifex** — the AGPL obligations apply even when used as a backend data pipeline, which is a real constraint for proprietary or permissively licensed downstream products.
- **markitdown (Microsoft)** — MIT. Lightweight wrapper that converts Office formats, HTML, PDF, images to Markdown (Office via mammoth/python-pptx/pandas → HTML → Markdown). ~90k GitHub stars. *Major limitations:* no built-in OCR (cannot handle scanned PDFs), strips PDF heading/list formatting to plain text, weak on complex tables/layouts. Good for clean Office docs; not a grounding solution (no coordinates). Still 0.x (breaking changes possible).
- **unstructured (Unstructured.io)** — Apache-2.0 open-source library + commercial API. Partitions documents into typed elements (titles, paragraphs, tables, images). The OSS library is explicitly "designed as a starting point for quick prototyping" with "significantly decreased performance on document and table extraction," no access to the VLM/fine-tuned OCR models, and no enrichment — those are API-only. Heavy system dependencies (poppler, tesseract, libreoffice).
- **Marker / Surya (Datalab)** — High-accuracy PDF→Markdown/JSON (Marker scored 76.1 on olmOCR-Bench among open tools). **License caveat:** Marker code is GPL; Surya code is Apache-2.0; **both use a restricted model-weights license (modified AI-Pubs OpenRAIL-M, free only for research/personal/startups under $2M (Marker) / $5M (Surya) revenue)**. Surya 2 (a ~650M-param VLM) does layout + OCR + tables and emits bounding boxes; latest releases through mid-2026. Datalab's hosted API + Chandra model offer a commercial path. Embeddable but license-encumbered for commercial OSS.
- **GROBID** — Apache-2.0. Specialized for scientific/scholarly PDFs → TEI/XML; ~0.87–0.90 F1 on reference parsing; extracts 68 fine-grained labels with bounding boxes. Production-ready, but Java-based (Python client over a web service) and narrow (academic documents).
- **Nougat (Meta)** — academic-paper PDF→Markdown VLM; largely superseded by newer VLM OCR; less actively maintained.
- **trafilatura** — Apache-2.0, the recommended HTML main-content extractor (mean F1 0.937 in OSTI's evaluation). Pure Python, fast, outputs TXT/Markdown/JSON/XML. Should be the HTML path's default.
- **VLM OCR models (self-hostable):** **Granite-Docling-258M** (Apache 2.0), **Surya 2** (OpenRAIL-M weights), **dots.ocr** (3B), **olmOCR-2** (82.4 on olmOCR-Bench, a +14.2-point gain over the Feb 2025 release, per Allen AI / arXiv 2510.19817), **DeepSeek-OCR / DeepSeek-OCR 2** (3B, "Contexts Optical Compression," 200k+ pages/day on one A100, ~$178/M pages on H100), **PaddleOCR-VL** (0.9B). October 2025 alone saw six major open OCR model releases. These need GPU + vLLM/llama.cpp infrastructure — powerful but heavy to embed directly.

**Hosted / API-only:**

- **Mistral OCR 3** (`mistral-ocr-2512`, released Dec 17, 2025) — API-only, proprietary (self-hosting offered for sensitive data). **$2 per 1,000 pages, $1 with batch** — the price-floor setter. Outputs Markdown + HTML table reconstruction (colspan/rowspan). Mistral's internal evaluations on real customer workflows show a 74% overall win rate over Mistral OCR 2 across forms, scanned documents, complex tables, and handwriting; strong on handwriting/forms/complex tables. *Caveat:* clean Markdown can "mask OCR hallucination errors" (digits silently flipped) — human-in-the-loop recommended for financial data. No documented SOC2/HIPAA/FedRAMP.
- **LlamaParse / LlamaCloud (LlamaIndex)** — API-only, credit-based (1,000 credits = $1, or $1.25 in some plans; 10k free credits/month). v2 simplified to tiers: Fast (1 credit/page, spatial text only, no Markdown), Cost-effective (3), Agentic (10), Agentic Plus (45). `extract_layout` adds bounding boxes. LlamaExtract does schema-based extraction. Good fit if you're already in the LlamaIndex ecosystem.
- **Reducto** — API-only, credit-based (~1,000 credits = $1 in North America), enterprise-focused. **Strongest provenance story among hosted parsers:** Parse responses expose blocks/chunks with normalized coordinates + page references; Extract attaches **per-field citations (page + bbox) plus confidence scores**. Agentic OCR multi-pass correction; SOC 2 Type II, HIPAA/BAA, ZDR, VPC/on-prem/air-gapped. Reports 99.24% extraction accuracy in a healthcare deployment. Premium pricing.
- **Azure AI Document Intelligence** (formerly Azure AI Form Recognizer; renamed 2023; now also branded "in Foundry Tools") — Read (OCR) **$1.50/1k pages** (≤1M), **$0.60/1k** (>1M); Layout (tables, structure, **Markdown output via `outputContentFormat=markdown`**, bounding boxes) **$10/1k** (a flat rate that also covers prebuilt Invoice/Receipt/ID models and already includes the underlying Read operation); custom extraction **$30/1k**; custom classification/splitting $3/1k. Returns **per-field bounding polygons (4-vertex) + confidence**. Free F0 tier (500 pages/mo). Mature, enterprise-grade, container-deployable (containers priced same as cloud). *(Verified against official Microsoft Learn / Microsoft Q&A sources; the public Azure pricing page renders its dollar figures via JavaScript.)*
- **Google Cloud Document AI** — Enterprise Document OCR **$1.50/1k** (≤5M), **$0.60/1k** (>5M); OCR add-ons +$6/1k; **Layout Parser $10/1k** (includes initial chunking, flat both tiers); Form Parser / Custom Extractor **$30/1k** (≤1M), **$20/1k** (>1M); custom-processor **hosting $0.05/hour per deployed version (~$438/yr)** — applies only to custom processors, not the pretrained OCR/Layout/Form processors; optional provisioned capacity "$300 for every extra page-per-minute per-month." Returns `boundingPoly` (pixel `vertices` + `normalizedVertices`) + confidence per element. 200+ languages, best-in-class handwriting; online requests often capped at 15 pages (use batch for more). *(Figures verbatim from the official Google Cloud pricing page.)*
- **AWS Textract** — Detect Document Text (OCR) ~$1.50/1k (first 1M), ~$0.60/1k (>1M); Analyze Document features billed separately and stack: Tables +$15/1k, Queries +$25/1k, Forms (and Forms+Tables+Queries combinations) up to ~$65/1k — the highest per-page rate among the cloud trio for full structured analysis. Industry-leading table cell/merged-cell relationship mapping; returns bounding boxes + confidence; specialized APIs (Expense, ID, Lending). Best when already on AWS. Bedrock Data Automation offers flat per-document pricing as an alternative path.
- **Chunkr** — open-source + hosted, Rust-based pipeline; layout analysis into typed segments with per-segment processing (fast OCR for text, VLM for tables/formulas), bounding boxes for citations, HTML/Markdown/JSON output, chunking. Self-hostable (~4 pages/s on an RTX 4090). Good "own-it" option with provenance.
- **omniai (OmniAI)** — hosted document-extraction API positioning against the cloud incumbents; smaller/less-proven; evaluate against your documents.

**Cloud OCR per-1,000-page comparison (US, pay-as-you-go):**

| Capability | Azure Document Intelligence | Google Document AI | AWS Textract |
|---|---|---|---|
| OCR / Read | $1.50 (≤1M); $0.60 (>1M) | $1.50 (≤5M); $0.60 (>5M) | ~$1.50 (≤1M); ~$0.60 (>1M) |
| Layout (tables/structure, Markdown) | $10 flat | $10 flat | Tables +$15 over OCR |
| Form / custom extraction | $30 | $30 (≤1M); $20 (>1M) | up to ~$65 (Forms+Tables+Queries) |
| Per-processor hosting fee | none (cloud) | $0.05/hr per custom version (~$438/yr) | none |
| Per-field bbox + confidence | Yes | Yes | Yes |

### (5) Layout/structure preservation, provenance, and grounding

Preserving layout is not cosmetic — it directly improves extraction accuracy *and* is the prerequisite for grounding. Reducto's own evaluations on scanned 10-K filings found structure-preserving parsing "improved retrieval relevance and graded answer correctness versus text-only OCR."

**Grounding** means every extracted value carries a pointer to its exact source location:
- **page number** (coarsest),
- **bounding box / coordinates** (visual, for PDF/image),
- **cell reference** (XLSX: `sheet!R{row}C{col}`),
- **character span** (text/Markdown: 0-indexed start/end offsets).

This matters for hallucination-free extraction because it converts an unverifiable assertion ("revenue was $X") into a checkable claim ("revenue was $X, per cell B12 on sheet 'FY23' / page 4 bbox [x0,y0,x1,y1]"). A reviewer or an automated validator can open the source and confirm. In a typed-graph pipeline, **each node and edge should store its provenance**, so the graph is auditable end-to-end and so conflicting values can be adjudicated by source.

**Which tools emit provenance:**
- **Docling** — page + bbox on every node (`DocItem.prov`); e.g. `table.prov[0].page_no` / `.bbox`. DocTags carries content + bbox + page index + structural role. Best-in-class for an OSS library; integrates with extraction frameworks (e.g., LangExtract) to map entities back to physical location for "100% traceability."
- **Azure / Google / AWS** — per-field bounding polygons/vertices + confidence scores.
- **Reducto** — per-field page + bbox citations + confidence.
- **Surya / Chunkr / Marker(JSON)** — bounding boxes per element/segment.
- **Claude Citations API** — char offsets (text), page numbers (PDF), or content-block indices (custom chunks).
- **PyMuPDF4LLM** — `to_json()` emits bounding boxes/layout per element (the Markdown output alone does not).
- **No provenance:** markitdown, plain Tesseract text, plain text extraction.

A subtle but important caveat for coordinate grounding via multimodal models: when you upload a PDF to Claude, "pages are rasterized to images server-side at dimensions you don't control, so the returned coordinates can't be reliably mapped back onto the page." To get reliable visual coordinates, rasterize pages yourself and send images, or use the Citations API (which gives char/page references, not bboxes).

### (6) How Claude's native features change build-vs-buy

Anthropic's stack is a genuine build-vs-buy lever:
- **Native PDF support (text + vision):** the system extracts text *and* converts each page to an image, so Claude reads charts/tables/handwriting. Available on the Claude API, Bedrock, Vertex AI, and Microsoft Foundry; all current models support it.
- **Files API** (`anthropic-beta: files-api-2025-04-14`): upload once, reference by `file_id` across calls — avoids re-encoding base64 on every turn (a real latency/payload win in agentic loops).
- **Citations API** (GA on Anthropic API and Vertex; also on Bedrock): chunks documents into sentences and returns answer text annotated with exact source references; `cited_text` does **not** count toward output tokens. Per Anthropic's Jan 2025 Citations announcement, internal evaluations show built-in citations "enhance recall accuracy by up to 15%" compared to prompt-engineered citation approaches. Tarun Amasa, CEO of Endex, reported: "With Anthropic's Citations, we reduced source hallucinations and formatting issues from 10% to 0% and saw a 20% increase in references per response." On Bedrock's Converse API, visual PDF analysis *requires* citations to be enabled.

**Limits and cost implications:**
- **100-page / 32 MB** hard limit per request (PDFs over 100 pages error out; on Claude.ai beyond 100 pages it falls back to text-only).
- Each page ≈ 1,500–3,000 text tokens **plus** image tokens; dense PDFs can exhaust context before the page limit. This makes Claude-native expensive at high volume vs. local extraction.
- Prompt caching + batch processing materially reduce repeat-analysis cost.

**When a Python library should lean on Claude directly:**
- Scanned/visually complex/low-to-moderate-volume documents where building OCR + layout + grounding is not worth it.
- When you want grounding (Citations) without building a sentence-chunker + offset-tracker yourself.
- Early-stage products optimizing for time-to-market over per-unit cost.

**When it should keep its own parsing layer:**
- High volume (token economics favor local extraction by ~1,000×).
- Documents > 100 pages / 32 MB.
- Need for deterministic, reproducible, offline, or air-gapped processing.
- Provider independence.

**Provider-agnostic fallback strategy (recommended):** wrap ingestion behind a single interface with pluggable backends. Default to local structure-preserving extraction (Docling/PyMuPDF4LLM); detect low-quality output (empty text layer, high garbled-char rate, table-detection failure) and **escalate** to (a) a local/hosted VLM OCR for scans, or (b) a multimodal model (Claude/Gemini) for visually complex pages; expose Claude Citations as one grounding provider among several, with a local char-span/bbox grounder as the fallback so the library never hard-depends on one vendor.

## Recommendations

**Staged adoption plan for the Python library:**

1. **Ship a minimal default that handles the 80% case cheaply and permissively.** Use MIT/Apache-licensed, pure-Python, local tools as the lightweight default dependency set:
   - PDF (digital): **Docling** (MIT) as the primary — it gives you structure + provenance + multi-format coverage in one dependency — or a thinner `pypdf`/`pdfplumber` path if you want to minimize footprint.
   - HTML: **trafilatura** (Apache-2.0).
   - XLSX: **openpyxl** (with `data_only=True` and explicit merged-cell handling).
   - DOCX: **python-docx** / **mammoth**.
   - Markdown/plain text: pass through (normalize encoding only).
   - Emit a normalized representation = Markdown for the LLM **plus** a structured sidecar (typed elements + page/cell/char-span/bbox provenance).

2. **Offer heavier capabilities behind `extras_require`, applying progressive disclosure.** Keep the core install small and the dependency tree clean:
   - `[ocr]` → local OCR (Tesseract via pytesseract, or Surya/RapidOCR) for scanned documents.
   - `[vlm]` → self-hosted VLM OCR (Granite-Docling, Surya 2, DeepSeek-OCR) for high-accuracy local scans (GPU).
   - `[hosted]` → clients for Mistral OCR 3 / LlamaParse / Reducto / Azure / Google / Textract.
   - `[anthropic]` → Claude native PDF + Citations grounding provider.
   - **Avoid AGPL/GPL in the default set.** PyMuPDF4LLM (AGPL) and Marker (GPL) should live only in an opt-in extra with a clear license warning, never as a hard default dependency, to keep the core permissively licensed.

3. **Make grounding mandatory in the data model, optional in the backend.** Define every extracted node/edge to carry a `provenance` field (document id + locator union: page, bbox, cell ref, char span). Backends that can't supply coordinates (markitdown, plain text) populate the coarsest available locator (page or char span); backends that can (Docling, cloud APIs, Reducto, Claude Citations) populate the finest.

4. **Route by format and quality gate, not by a single hammer.** Implement the decision table below as the default router, with an escalation ladder: cheap local extraction → quality check → OCR/VLM → multimodal model.

**Decision table — input format → recommended ingestion path:**

| Input format | Recommended path | Rationale |
|---|---|---|
| **PDF (digital/text)** | Convert via Docling/PyMuPDF4LLM → Markdown + structured sidecar | Text layer is reliable; ~1,000× cheaper than OCR; preserves tables + provenance |
| **PDF (scanned/image-only)** | Native VLM OCR (Surya/Granite-Docling local; Mistral OCR 3/Azure/Google hosted) → fall back to multimodal model for visually complex pages | No text layer; needs OCR; VLM beats Tesseract on layout/tables/handwriting |
| **DOCX** | Native parse (python-docx/mammoth); resolve tracked changes; convert to PDF first if image-heavy and you need Claude citations | Preserves styles/tables/footnotes; avoids tracked-change duplication |
| **XLSX** | Native parse (openpyxl), structured rows/cells with cell-ref provenance; `data_only=True` | Merged cells/formulas/hidden rows/type inference demand structured handling, not flattening |
| **HTML** | trafilatura main-content extraction → Markdown | Removes boilerplate/nav/ads; preserves semantic structure; token-efficient |
| **Markdown** | Pass through (normalize encoding) | Already LLM-native and structured |
| **Plain text** | Pass through; optional light structure inference | No structure to preserve |
| **Image (photo/scan)** | Multimodal model or VLM OCR; pre-process (deskew/denoise) for classic OCR | Vision required; handwriting → Mistral OCR 3 / cloud OCR |

**Benchmarks/thresholds that should change the routing:**
- If extracted text has >~5–10% replacement/garbled characters or an empty text layer → escalate to OCR.
- If table-structure detection confidence is low or merged cells are present → preserve as HTML/JSON, not Markdown pipes.
- If volume > ~50k pages/month → prefer local/self-hosted over per-page hosted APIs on cost grounds (Mistral batch at $1/1k is the hosted floor; self-hosted VLM ~$178/M pages on H100).
- If documents exceed 100 pages / 32 MB → cannot use Claude-native; chunk or use local/hosted parser.
- If grounding/audit is required (finance, healthcare, legal) → mandate a coordinate-emitting backend (Docling, Reducto, cloud APIs, or Claude Citations).

## Caveats

- **Vendor benchmark claims are self-reported.** Mistral's "74% win rate," Reducto's "99.24% accuracy," and "up to 20% over cloud APIs" come from internal/vendor evaluations; independent results are mixed (e.g., Hacker News reports Mistral OCR strong on equations/cursive but weaker on complex layouts). Always pilot on your own document mix before committing.
- **Pricing moves fast and varies by region/tier.** The cloud figures here are US pay-as-you-go and were cross-checked against official Microsoft/Google sources in mid-2026; Azure's pricing page renders numbers via JavaScript, so reconfirm the live page for exact current figures. Per-feature billing (especially Textract, where Tables/Queries/Forms stack) compounds quickly at scale.
- **"Clean-looking" OCR output can hide silent errors.** High-fidelity Markdown can mask flipped digits; for financial/medical typed-graph extraction, keep a human-in-the-loop or automated validator that re-checks each grounded value against its source coordinate.
- **License terms can change and weight-licenses differ from code-licenses.** Surya/Marker code vs. weights carry different terms; PyMuPDF4LLM's AGPL applies even to backend pipelines. Verify license fit for your distribution model before depending on any tool, and re-verify on upgrades.
- **Model/library churn is high.** The VLM-OCR space saw six major releases in October 2025 alone; today's best model may be superseded within a quarter. Design the ingestion layer for swappable backends so you can adopt improvements without re-architecting.
- **DeepSeek-OCR 2 and similar very-recent models** (early 2026) are promising but newly released; treat throughput/accuracy figures as preliminary until independently reproduced.

## References

[1] [Granite Docling | IBM Granite](https://www.ibm.com/granite/docs/models/docling)
[2] [IBM Granite-Docling: End-to-end document understanding](https://www.ibm.com/new/announcements/granite-docling-end-to-end-document-conversion)
[3] [Docling GitHub](https://github.com/docling-project/docling)
[4] [Docling: An Efficient Open-Source Toolkit (arXiv 2501.17887)](https://arxiv.org/html/2501.17887v1)
[5] [Docling Document reference](https://docling-project.github.io/docling/reference/docling_document/)
[6] [Docling vendor profile — IDP-Software](https://idp-software.com/vendors/docling/)
[7] [PDF support — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/pdf-support)
[8] [Files API — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/files)
[9] [Vision — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/vision)
[10] [Citations — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/citations)
[11] [Introducing Citations on the Anthropic API](https://claude.com/blog/introducing-citations-api)
[12] [Anthropic's new Citations API — Simon Willison](https://simonwillison.net/2025/Jan/24/anthropics-new-citations-api/)
[13] [Citations API and PDF support for Claude in Amazon Bedrock — AWS](https://aws.amazon.com/about-aws/whats-new/2025/06/citations-api-pdf-claude-models-amazon-bedrock/)
[14] [Mistral OCR | Mistral AI](https://mistral.ai/news/mistral-ocr/)
[15] [Introducing Mistral OCR 3 | Mistral AI](https://mistral.ai/news/mistral-ocr-3/)
[16] [Mistral OCR 3 Technical Review — PyImageSearch](https://pyimagesearch.com/2025/12/23/mistral-ocr-3-technical-review-sota-document-parsing-at-commodity-pricing/)
[17] [Mistral launches OCR 3 — VentureBeat](https://venturebeat.com/technology/mistral-launches-ocr-3-to-digitize-enterprise-documents-touts-74-win-rate)
[18] [Unstructured open-source overview](https://docs.unstructured.io/open-source/introduction/overview)
[19] [Unstructured GitHub](https://github.com/Unstructured-IO/unstructured)
[20] [MarkItDown — InfoWorld](https://www.infoworld.com/article/3963991/markitdown-microsofts-open-source-tool-for-markdown-conversion.html)
[21] [markitdown GitHub](https://github.com/microsoft/markitdown)
[22] [Python MarkItDown — Real Python](https://realpython.com/python-markitdown/)
[23] [LlamaParse Pricing | LlamaIndex](https://www.llamaindex.ai/pricing)
[24] [LlamaParse v2 announcement](https://www.llamaindex.ai/blog/introducing-llamaparse-v2-simpler-better-cheaper)
[25] [LlamaParse Pricing — Developer Docs](https://developers.llamaindex.ai/llamaparse/general/pricing/)
[26] [Marker GitHub](https://github.com/datalab-to/marker)
[27] [Surya GitHub](https://github.com/datalab-to/surya)
[28] [surya-ocr PyPI](https://pypi.org/project/surya-ocr/)
[29] [Datalab vendor profile — IDP-Software](https://idp-software.com/vendors/datalab/)
[30] [PyMuPDF4LLM GitHub](https://github.com/pymupdf/pymupdf4llm)
[31] [PyMuPDF4LLM docs](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)
[32] [PyMuPDF FAQ](https://pymupdf.readthedocs.io/en/latest/faq/index.html)
[33] [Azure Document Intelligence FAQ — Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/faq?view=doc-intel-4.0.0)
[34] [Azure Document Intelligence pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/)
[35] [Azure AI Document Intelligence Processing Guide — Signisys](https://www.signisys.com/blog/azure-ai-document-intelligence/)
[36] [Cost of Document Intelligence — Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5665475/what-is-the-cost-of-document-intellegence-service)
[37] [AWS Textract pricing](https://aws.amazon.com/textract/pricing/)
[38] [Document AI Cost Comparison 2026](https://aiproductivity.ai/blog/document-ai-cost-comparison/)
[39] [AWS Intelligent Document Processing Cost Calculator — Tech 42](https://www.tech42consulting.com/aws-idp-cost-calculator)
[40] [Google Document AI pricing](https://cloud.google.com/document-ai/pricing)
[41] [AWS Textract vs Google Document AI — Braincuber](https://www.braincuber.com/blog/aws-textract-vs-google-document-ai-ocr-comparison)
[42] [GROBID GitHub](https://github.com/grobidOrg/grobid)
[43] [GROBID Documentation](https://grobid.readthedocs.io/en/latest/Introduction/)
[44] [Benchmarking Document Parsers on Math Formula Extraction (arXiv 2512.09874)](https://arxiv.org/html/2512.09874v1)
[45] [Docling provenance / LangExtract integration — DEV](https://dev.to/_aparna_pradhan_/the-perfect-extraction-unlocking-unstructured-data-with-docling-langextract-1j3b)
[46] [Full table bounding boxes — Docling Discussion](https://github.com/docling-project/docling/discussions/2368)
[47] [Reducto vs LlamaParse](https://llms.reducto.ai/reducto-vs-llamaparse)
[48] [Reducto Pricing](https://reducto.ai/pricing)
[49] [Best LLM-Ready Document Parsers in 2025 — Reducto](https://llms.reducto.ai/best-llm-ready-document-parsers-2025)
[50] [HTML vs Markdown for LLM ingestion — ReleasePad](https://www.releasepad.io/blog/html-vs-markdown-the-optimal-format-for-llm-content-ingestion/)
[51] [PDF vs Markdown vs TXT — MDisBetter](https://mdisbetter.com/blog/best-format-for-llm-input-pdf-vs-markdown-vs-txt)
[52] [TableEval (arXiv 2506.03949)](https://arxiv.org/pdf/2506.03949)
[53] [S3Eval (arXiv 2310.15147)](https://arxiv.org/pdf/2310.15147)
[54] [Table Extraction using LLMs — Nanonets](https://nanonets.com/blog/table-extraction-using-llms-unlocking-structured-data-from-documents/)
[55] [openpyxl usage docs](https://openpyxl.readthedocs.io/en/stable/editing_worksheets.html)
[56] [openpyxl merged cells discussion — Google Groups](https://groups.google.com/g/openpyxl-users/c/6G7lLDJsy8E)
[57] [trafilatura evaluation](https://trafilatura.readthedocs.io/en/latest/evaluation.html)
[58] [An Evaluation of Main Content Extraction Libraries — OSTI](https://www.osti.gov/servlets/purl/2429881)
[59] [7 Best Open-Source OCR Models 2025 — E2E Networks](https://www.e2enetworks.com/blog/complete-guide-open-source-ocr-models-2025)
[60] [DeepSeek-OCR Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-OCR)
[61] [Chunkr Launch — Y Combinator](https://www.ycombinator.com/launches/Mud-chunkr-open-source-document-parsing-you-can-own)
[62] [Supercharge your OCR Pipelines with Open Models — Hugging Face](https://huggingface.co/blog/ocr-open-models)
[63] [Claude AI File Uploading & Reading Capabilities — Data Studios](https://www.datastudios.org/post/claude-ai-file-uploading-reading-capabilities-detailed-overview)
[64] [Mistral OCR 3 — MarkTechPost](https://www.marktechpost.com/2025/12/19/mistral-ai-releases-ocr-3-a-smaller-optical-character-recognition-ocr-model-for-structured-document-ai-at-scale/)