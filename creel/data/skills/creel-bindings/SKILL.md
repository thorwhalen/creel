---
name: creel-bindings
description: >-
  Write creel bindings: map each grammar element to an extractor strategy. Use
  when you need to choose an extractor strategy for a node-type or edge-type,
  decide pattern vs query vs LLM extraction, write regex_node/regex_edge over
  prose, or table_map/sql/json_query over structured sources. Covers the binding
  mental model ({element_id: (strategy, params)} or a bare callable), id
  templates and casts, endpoint templates for edges, exclude_groups, cluster
  bindings (cluster_llm), registering a custom extractor strategy, and how unbound
  elements behave (on_missing_binding). Trigger on: map grammar elements to
  extractors, route prose to regex and tables to query, bind a funds/measures
  edge, derive node ids, id_template/id_from, register_extractor a custom strategy,
  cluster_llm one-pass extraction, on_missing_binding, fix a binding error.
metadata:
  audience: users
---

# creel-bindings — map each grammar element to an extractor

A **grammar** (`GraphSpec`) says *what* the graph contains; **bindings** say *how*
each element is populated from your sources. The two layers are physically separate
and joined by element id, so one grammar pairs with many extraction strategies.
Pipeline: `creel-grammar` (define elements) → **creel-bindings** (this skill) →
`creel-extract` (run `extract`) → `creel-evaluation` (verify the result).

## Mental model

`extractors` is **one entry per grammar element id**. Each value is one of:

```python
bindings = {
    "donor":  ("regex_node", {"pattern": ...}),   # (strategy_name, pure-data params)
    "funds":  ("table_map",  {...}),               # another strategy
    "outcome": ("llm", {}),                         # LLM default — see creel-ai
    "indicator": my_callable,                       # a bare (ctx) -> Extraction callable
}
```

- The **`(strategy, params)` tuple** names a registered strategy and passes its
  config as **pure data** (no engine internals interpolated from untrusted input).
- A **bare callable** `(ExtractionContext) -> Extraction` is used directly — your
  escape hatch when no declarative strategy fits.
- `params` are exactly the strategy's keyword arguments. The **pattern** strategies
  validate them strictly: a malformed config raises an informative `ValueError`
  **naming the element and strategy**, e.g. `binding for 'donor' ('regex_node') has
  invalid params {...}`. The **query** strategies are more permissive — they ignore
  unrecognised keys, so a typo in an `attributes`/column key fails *silently* (no
  error, just a missing attribute). Double-check query mappings.

`available_extractors()` lists registered strategy names; built-ins are
`regex_node`, `regex_edge`, `function`, `table_map`, `sql`, `json_query`, `llm`,
and `cluster_llm` (one LLM pass over several coupled types — see *Cluster binding*).

**Route by source shape (decision D5 — cheapest strategy that fits):**

| Source            | Use                         | Cost / determinism            |
|-------------------|-----------------------------|-------------------------------|
| Regular prose     | `regex_node` / `regex_edge` | free, `confidence=1.0`, exact |
| Tables (`list[dict]`) | `table_map` (or `sql`)  | free (sql needs `[query]`)    |
| JSON              | `json_query` (`[query]`)    | cheap                         |
| Messy / narrative | `("llm", {})`               | costs tokens — see `creel-ai` |

## id derivation (shared by every strategy)

Ids must be **stable and deterministic**. Every interpolated value is **slugged**:
casefolded, Unicode alphanumerics kept, the rest collapsed to single dashes
(`"Foundation Alpha"` → `foundation-alpha`). Same input → same id → one-line
diffs. Three ways to get a node id: `id_template="output:{output_code}"` (format
over record/groups), `id_from="code"` (slug one column — table strategies only),
or neither — the fallback is `type:<row-index>` for table/query strategies and a
slug of the **whole matched text** for regex (no hashing anywhere; ids stay
human-readable and stable).

## Pattern family — prose → regex (no extra deps)

**`regex_node`** — each match becomes a node; **named capture groups become
attributes**.

```python
"donor": ("regex_node", {
    "pattern": r"Donor:\s*(?P<name>[A-Za-z ]+?)\s*\(ref\s*(?P<org_code>\d+)\)",
    "id_attribute": "name",          # slug of this group is the id; else slug the whole match
    "casts": {"org_code": "int"},    # cast captured strings where the grammar wants numbers
})
```

- `node_type` defaults to the element id; `flags` passes `re.IGNORECASE` etc.
- `id_attribute` picks which group seeds the id; omit it to slug the whole matched text.

**`regex_edge`** — each match becomes a first-class edge. Endpoint node ids are
built from **templates over the captured groups**; groups consumed only as
endpoint refs go in `exclude_groups` so they don't leak into edge attributes.

```python
"funds": ("regex_edge", {
    "pattern": r"(?P<donor>[A-Za-z ]+?) commits (?P<currency>[A-Z]{3}) "
               r"(?P<amount>[\d,]+) to (?P<project>PRJ-\d+)",
    "source_id_template": "donor:{donor}",     # must match the node ids you emit
    "target_id_template": "project:{project}",
    "casts": {"amount": "int"},
    "exclude_groups": ("donor", "project"),    # endpoint refs, not attributes
})
# -> edge funds  donor:<slug> -> project:<slug>, attrs {currency, amount}
```

The endpoint templates must produce ids that **match the nodes another binding
emits** — that's how edges connect to nodes. Casts and slugging behave exactly as
in `regex_node`.

## Query family — structured sources

All three share a record→element **mapping** (pure data). Keys: `kind`
(`"node"`|`"edge"`, default node), `type` (element type, default = element id),
`id_template`/`id_from`, `source_template`/`target_template` (required for edges),
`attributes` (`{attr: column}`), `casts` (`{attr: "int"|"float"|"number"}`).

**`table_map`** — map rows of a table source (`records_source` names it; the
source must be a `TABLE`, i.e. `list[dict]`). Zero extra deps.

```python
# nodes
"project": ("table_map", {
    "records_source": "funding", "kind": "node", "type": "project",
    "id_template": "project:{project_title}", "attributes": {"title": "project_title"},
}),
# edges — endpoint templates wire rows to existing node ids
"funds": ("table_map", {
    "records_source": "funding", "kind": "edge", "type": "funds",
    "source_template": "donor:{donor_name}", "target_template": "project:{project_title}",
    "attributes": {"amount": "amt"}, "casts": {"amount": "int"},
}),
```

**`sql`** (extra `[query]`, needs `duckdb`) — run a **parameterized** DuckDB query
over the table, then map result rows. For filter/join/aggregate. Bind values as
`params=[...]` referenced by `?` — never string-interpolate untrusted values.

```python
"donor": ("sql", {
    "records_source": "t", "sql": "SELECT * FROM t WHERE name = ?", "params": ["Beta"],
    "id_template": "donor:{code}", "attributes": {"name": "name"},
})
```

**`json_query`** (extra `[query]`, needs `jmespath`) — `select` a JMESPath
expression, optional `where` equality/comparison filter
(`$gt`/`$lt`/`$in`/`$ne`), then map.

```python
"thing": ("json_query", {
    "records_source": "j", "select": "items", "where": {"v": {"$gt": 2}},
    "id_template": "thing:{id}", "attributes": {"value": "v"},
})
```

## Cluster binding — one pass over coupled types

When several types come out of **one** extractor call (e.g. an LLM returning
donors *and* their funding edges together), bind them as a cluster via the dict
form with `elements` so the extractor runs **once** for the whole set, not per
element (D-OP8). The dict's `element_id` key is then just a label.

Use the **`cluster_llm`** strategy: it reads the whole `elements` set, asks for one
JSON array per type, and emits instances of *each* in a single pass — preserving
the cross-type consistency that separate passes would break. (Plain `("llm", {})`
only emits its *one* element type, so it is the wrong choice for a cluster.)

```python
"donors_and_funds": {"strategy": "cluster_llm", "config": {},
                     "elements": ("donor", "funds")},  # emits BOTH in one pass
```

Most pattern/table bindings stay per-element; reach for a cluster only when the
types are genuinely produced together (needs `services={"llm": ...}` — see `creel-ai`).

## Custom strategies — register once, name everywhere

A one-off needs no registration: pass a bare `(ExtractionContext) -> Extraction`
callable as the binding value (the escape hatch). When a strategy is **reusable**
across bindings, register a factory `(**config) -> Extractor` under a name and then
refer to it by string like any built-in (open-closed — new mechanisms plug in
without touching old ones):

```python
from creel import register_extractor, Extraction, ExtractedNode

@register_extractor("upper_words")          # factory: (**config) -> Extractor
def make_upper_words(*, min_len=2):
    def extract_upper(ctx):                  # an Extractor: (ExtractionContext) -> Extraction
        text = "\n".join(s.content for s in ctx.sources.texts())
        return Extraction(nodes=[
            ExtractedNode(id=f"{ctx.element_type.id}:{w.lower()}",
                          type=ctx.element_type.id, attributes={"name": w})
            for w in text.split() if w.isupper() and len(w) >= min_len])
    return extract_upper

bindings = {"org": ("upper_words", {"min_len": 2})}   # now usable by name; in available_extractors()
```

Third-party packages can ship strategies via the `creel.extractors` entry-point
group — they auto-register on import, so `available_extractors()` picks them up with
no wiring. (Custom *verifiers* register the same way — see `creel-evaluation`.)

## Unbound elements — `on_missing_binding`

A grammar element with no binding is handled by `extract(..., on_missing_binding=)`:

- `"schema_as_extractor"` (default) — fall back to the LLM, using the element's
  `description` as the instruction (see `creel-ai`). Requires the LLM layer.
- `"skip"` — leave it unpopulated. Best for deterministic-only runs.
- `"error"` — raise, listing the unbound element ids. Use to assert full coverage.

Either way, `graph.report["unbound_elements"]` lists what had no binding. Edges
whose endpoint ids don't resolve to a node are dropped and listed in
`graph.report["skipped_edges"]` — usually an endpoint-template/id-template mismatch.

## End-to-end (verified)

```python
from creel.facade import extract
from creel.sources import Source, SourceBundle, TABLE

# donors from PROSE (regex_node); project + funds from a TABLE (table_map)
sources = SourceBundle([
    Source("agreement", "Donor: Foundation Alpha (ref 12345)."),
    Source("funding", [{"donor_name": "Foundation Alpha",
                        "project_title": "Clean Water", "amt": "1,000,000"}], kind=TABLE),
])
bindings = {
    "donor": ("regex_node", {
        "pattern": r"Donor:\s*(?P<name>[A-Za-z ]+?)\s*\(ref\s*(?P<org_code>\d+)\)",
        "id_attribute": "name"}),
    "project": ("table_map", {
        "records_source": "funding", "kind": "node", "type": "project",
        "id_template": "project:{project_title}", "attributes": {"title": "project_title"}}),
    "funds": ("table_map", {
        "records_source": "funding", "kind": "edge", "type": "funds",
        "source_template": "donor:{donor_name}", "target_template": "project:{project_title}",
        "attributes": {"amount": "amt"}, "casts": {"amount": "int"}}),
}
graph = extract(sources, spec, bindings, on_missing_binding="skip")
# -> donor:foundation-alpha, project:clean-water, funds edge with amount=1000000
```

## Checklist

1. One entry per element id; route prose→regex, tables→query, messy→`("llm", {})`.
2. Make edge `source_template`/`target_template` (or regex endpoint templates)
   produce ids that **match** the node bindings' `id_template`/`id_attribute`.
3. `casts` every numeric attribute the grammar declares as a number.
4. `exclude_groups` regex groups used only as endpoint refs.
5. Pick `on_missing_binding`; check `report["unbound_elements"]` and
   `report["skipped_edges"]` after extracting.
