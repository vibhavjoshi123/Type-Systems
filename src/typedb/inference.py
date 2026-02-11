"""TypeDB 3.x function management (replaces 2.x inference rules).

In TypeDB 3.x, rules are replaced by functions that must be explicitly
invoked in queries. Functions use the 'fun' keyword and return streams
or single values.

From ARCHITECTURE_PLAN.md Phase 1 Task: typedb_inference.py (P2).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.typedb.client import TypeDBClient

logger = logging.getLogger(__name__)


@dataclass
class TypeDBFunction:
    """A TypeDB 3.x function definition (replaces 2.x InferenceRule)."""

    name: str
    signature: str
    body: str
    description: str = ""

    def to_typeql(self) -> str:
        """Convert to a TypeQL function definition."""
        return f"define\nfun {self.name}{self.signature}:\n{self.body}"


# Built-in functions (replaces BUILT_IN_RULES)
BUILT_IN_FUNCTIONS: list[TypeDBFunction] = [
    TypeDBFunction(
        name="customers_at_risk",
        signature="() -> { customer }",
        body=(
            "    match\n"
            "        $c isa customer, has health-score $hs;\n"
            "        $hs < 70.0;\n"
            "    return { $c };"
        ),
        description="Find customers with health score below 70 (at-risk).",
    ),
]


# Backward compatibility aliases
InferenceRule = TypeDBFunction
BUILT_IN_RULES = BUILT_IN_FUNCTIONS


class InferenceManager:
    """Manage TypeDB 3.x functions for the hypergraph.

    In TypeDB 3.x, functions replace rules. Functions are defined in schema
    transactions and explicitly invoked using the 'in' keyword in match queries.
    """

    def __init__(self, client: TypeDBClient) -> None:
        self.client = client
        self._functions: dict[str, TypeDBFunction] = {
            f.name: f for f in BUILT_IN_FUNCTIONS
        }

    @property
    def rules(self) -> dict[str, TypeDBFunction]:
        """All registered functions (backward-compatible property name)."""
        return dict(self._functions)

    @property
    def functions(self) -> dict[str, TypeDBFunction]:
        """All registered TypeDB functions."""
        return dict(self._functions)

    def register_rule(self, rule: TypeDBFunction) -> None:
        """Register a new function (backward-compatible method name)."""
        self._functions[rule.name] = rule
        logger.info("Registered function: %s", rule.name)

    def register_function(self, func: TypeDBFunction) -> None:
        """Register a new TypeDB function."""
        self._functions[func.name] = func
        logger.info("Registered function: %s", func.name)

    def unregister_rule(self, name: str) -> TypeDBFunction | None:
        """Remove a registered function by name."""
        func = self._functions.pop(name, None)
        if func:
            logger.info("Unregistered function: %s", name)
        return func

    async def load_rules(self) -> int:
        """Load all registered functions into the TypeDB schema.

        Returns the number of functions loaded.
        """
        if not self.client.is_connected:
            logger.warning("TypeDB not connected; skipping function loading")
            return 0

        loaded = 0
        for func in self._functions.values():
            typeql = func.to_typeql()
            try:
                await self.client.load_schema(typeql)
                loaded += 1
                logger.info("Loaded function: %s", func.name)
            except Exception as exc:
                if "already exists" in str(exc):
                    logger.info("Function already loaded: %s", func.name)
                    loaded += 1
                else:
                    logger.exception(
                        "Failed to load function: %s", func.name
                    )

        return loaded

    async def query_with_inference(
        self,
        typeql: str,
        *,
        inference: bool = True,
    ) -> list[dict]:
        """Execute a query (functions are invoked explicitly in 3.x).

        In TypeDB 3.x, there is no inference toggle. Functions are called
        explicitly within match clauses using the 'in' keyword.
        """
        return await self.client.query(typeql)

    def get_rule(self, name: str) -> TypeDBFunction | None:
        """Get a function by name."""
        return self._functions.get(name)

    def list_rules(self) -> list[TypeDBFunction]:
        """List all registered functions."""
        return list(self._functions.values())
