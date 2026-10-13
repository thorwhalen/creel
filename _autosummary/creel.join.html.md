# creel.join

Join the grammar and the extraction-metadata layers into a runnable plan.

Per decision D7 this is a pure equijoin by element id: for every node-type and
edge-type in the `GraphSpec`, find its `ExtractorBinding` (if any) and
resolve the concrete `Extractor`. Elements with no binding fall back to a
`schema_as_extractor` factory when one is supplied (the progressive-disclosure
default), otherwise they are reported as `unbound`.

The result, a [`ResolvedPlan`](#creel.join.ResolvedPlan), is what the facade maps over.

### Module Attributes

| [`SchemaAsExtractor`](#creel.join.SchemaAsExtractor)   | A factory `(element_type, spec) -> Extractor` used when an element has no binding.   |
|----------------------------------------------------------------------|--------------------------------------------------------------------------------------|

### Functions

| [`join`](#creel.join.join)(spec, bindings, \*[, schema_as_extractor])   | Equijoin `spec` with `bindings` by element id into a [`ResolvedPlan`](#creel.join.ResolvedPlan).   |
|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|

### Classes

| [`ResolvedPlan`](#creel.join.ResolvedPlan)(steps, unbound)                | The full set of resolved extraction steps plus any unbound element ids.          |
|----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`ResolvedStep`](#creel.join.ResolvedStep)(element_id, element_type, ...) | One element of the plan: the element(s), the resolved extractor, and the source. |

### *class* creel.join.ResolvedPlan(steps, unbound)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The full set of resolved extraction steps plus any unbound element ids.

### *class* creel.join.ResolvedStep(element_id, element_type, extractor, binding_source, element_types=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One element of the plan: the element(s), the resolved extractor, and the source.

`element_types` is the cluster this step covers (D-OP8); for an ordinary
per-element step it is just `(element_type,)`.

### creel.join.SchemaAsExtractor

A factory `(element_type, spec) -> Extractor` used when an element has no binding.

alias of `Callable`[[[`ElementType`](creel.spec.model.html.md#creel.spec.model.ElementType), [`GraphSpec`](creel.spec.model.html.md#creel.spec.model.GraphSpec)], [`Extractor`](creel.html.md#creel.Extractor)]

### creel.join.join(spec, bindings, , schema_as_extractor=None)

Equijoin `spec` with `bindings` by element id into a [`ResolvedPlan`](#creel.join.ResolvedPlan).

Cluster bindings (`binding.elements`) are resolved first into one multi-element
step each (invoked once). Remaining elements resolve per-element. Node-types are
produced before edge-types so the facade adds nodes before the edges that
reference them.

* **Return type:**
  [`ResolvedPlan`](#creel.join.ResolvedPlan)
