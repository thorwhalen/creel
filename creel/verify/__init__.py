"""creel evaluation layer: pluggable verifiers (not hardcoded equality).

Re-exports the verifier contract (:mod:`creel.verify.protocol`), the kind taxonomy
(:mod:`creel.verify.kinds`), the natural-language ``llm_rubric`` (:mod:`creel.verify.rubric`),
and the registry. Importing this package registers the built-in verifier kinds.
"""

from creel.verify.graph_match import GraphMatch
from creel.verify.kinds import (
    Composite,
    ExactMatch,
    NormalizedMatch,
    NumericTolerance,
    SchemaConstraint,
    SemanticSimilarity,
    SetMatch,
)
from creel.verify.protocol import Verdict, VerificationContext, Verifier
from creel.verify.registry import (
    available_verifiers,
    build_verifier,
    register_verifier,
)
from creel.verify.rubric import LLMRubric, schema_description_verifier

__all__ = [
    "Verdict",
    "VerificationContext",
    "Verifier",
    "ExactMatch",
    "NormalizedMatch",
    "NumericTolerance",
    "SetMatch",
    "SchemaConstraint",
    "SemanticSimilarity",
    "Composite",
    "GraphMatch",
    "LLMRubric",
    "schema_description_verifier",
    "available_verifiers",
    "build_verifier",
    "register_verifier",
]
