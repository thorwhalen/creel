# creel.verify.registry

Verifier discovery: a decorator registry + entry points (group `creel.verifiers`).

Mirrors `creel.extract.registry` (decision D12). A registered factory is
`(**config) -> Verifier`.

### Functions

| [`available_verifiers`](#creel.verify.registry.available_verifiers)()            | Return the sorted names of all registered verifiers (incl.                     |
|-----------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`build_verifier`](#creel.verify.registry.build_verifier)(name, \*\*config) | Instantiate the named verifier with its `config`.                              |
| [`get_verifier_factory`](#creel.verify.registry.get_verifier_factory)(name)       | Return the registered factory for `name` (loading entry points on first miss). |
| [`register_verifier`](#creel.verify.registry.register_verifier)(name)          | Decorator registering a verifier *factory* under `name`.                       |

### creel.verify.registry.available_verifiers()

Return the sorted names of all registered verifiers (incl. entry points).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### creel.verify.registry.build_verifier(name, \*\*config)

Instantiate the named verifier with its `config`.

* **Return type:**
  [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)

### creel.verify.registry.get_verifier_factory(name)

Return the registered factory for `name` (loading entry points on first miss).

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis), [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)]

### creel.verify.registry.register_verifier(name)

Decorator registering a verifier *factory* under `name`.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis), [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)]], [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis), [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)]]
