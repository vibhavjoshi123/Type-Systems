"""Tests for TypeDB 3.x function management (replaces 2.x inference rules)."""

from src.typedb.inference import (
    BUILT_IN_FUNCTIONS,
    BUILT_IN_RULES,
    InferenceManager,
    InferenceRule,
    TypeDBFunction,
)


class TestTypeDBFunction:
    def test_to_typeql(self):
        func = TypeDBFunction(
            name="test_func",
            signature="($x: customer) -> { deal }",
            body=(
                "    match\n"
                "        ($x, $d) isa context-hyperedge;\n"
                "        $d isa deal;\n"
                "    return { $d };"
            ),
        )
        typeql = func.to_typeql()
        assert "fun test_func" in typeql
        assert "define" in typeql
        assert "match" in typeql
        assert "return" in typeql

    def test_built_in_functions(self):
        assert len(BUILT_IN_FUNCTIONS) >= 1
        assert BUILT_IN_FUNCTIONS[0].name == "customers_at_risk"

    def test_backward_compat_aliases(self):
        """InferenceRule and BUILT_IN_RULES are aliases for 3.x types."""
        assert InferenceRule is TypeDBFunction
        assert BUILT_IN_RULES is BUILT_IN_FUNCTIONS


class TestInferenceManager:
    def test_register_function(self):
        class MockClient:
            is_connected = False

        mgr = InferenceManager(MockClient())
        func = TypeDBFunction(
            name="new_func",
            signature="() -> { deal }",
            body="    match $d isa deal, has deal-value $v; $v > 500000.0;\n    return { $d };",
        )
        mgr.register_rule(func)
        assert "new_func" in mgr.rules
        assert "new_func" in mgr.functions

    def test_unregister_function(self):
        class MockClient:
            is_connected = False

        mgr = InferenceManager(MockClient())
        removed = mgr.unregister_rule("customers_at_risk")
        assert removed is not None
        assert "customers_at_risk" not in mgr.rules

    def test_get_function(self):
        class MockClient:
            is_connected = False

        mgr = InferenceManager(MockClient())
        func = mgr.get_rule("customers_at_risk")
        assert func is not None
        assert func.name == "customers_at_risk"

    def test_list_functions(self):
        class MockClient:
            is_connected = False

        mgr = InferenceManager(MockClient())
        funcs = mgr.list_rules()
        assert len(funcs) >= 1
