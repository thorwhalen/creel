# creel.render

The renderer contract — the three-layer annotated-graph renderers consume (D15).

creel ships the *contract*, not concrete renderers (those live in consumer packages).
An [`AnnotatedGraph`](#creel.render.AnnotatedGraph) is the three layers: the graph (the SSOT), a standoff
[`Annotation`](creel.annotate.html.md#creel.annotate.Annotation) overlay (insights/comments/codings keyed by
target), and optional presentation hints. A [`GraphRenderer`](#creel.render.GraphRenderer) turns one into a
[`RenderArtifact`](#creel.render.RenderArtifact) (bytes/text + media type).

Use [`creel.view`](creel.view.html.md#module-creel.view) for the dependency-free projections (DOT/Mermaid/Cytoscape/
tables) that concrete renderers build on.

### Classes

| [`AnnotatedGraph`](#creel.render.AnnotatedGraph)(graph[, annotations, ...])       | The render contract: graph + standoff annotation overlay + presentation hints.                                                                    |
|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| [`GraphRenderer`](#creel.render.GraphRenderer)(\*args, \*\*kwargs)               | Render an [`AnnotatedGraph`](#creel.render.AnnotatedGraph) into a [`RenderArtifact`](#creel.render.RenderArtifact). |
| [`RenderArtifact`](#creel.render.RenderArtifact)(content, media_type[, metadata]) | The output of a renderer: content (str/bytes/dict) + its media type.                                                                              |

### *class* creel.render.AnnotatedGraph(graph, annotations=(), presentation=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The render contract: graph + standoff annotation overlay + presentation hints.

#### annotations_for(element_id)

Return the annotations whose target is (or starts at) `element_id`.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Annotation`](creel.annotate.html.md#creel.annotate.Annotation)]

### *class* creel.render.GraphRenderer(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Render an [`AnnotatedGraph`](#creel.render.AnnotatedGraph) into a [`RenderArtifact`](#creel.render.RenderArtifact).

#### render(graph, , options=None)

Produce the rendered artifact.

* **Return type:**
  [`RenderArtifact`](#creel.render.RenderArtifact)

### *class* creel.render.RenderArtifact(content, media_type, metadata=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The output of a renderer: content (str/bytes/dict) + its media type.
