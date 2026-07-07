"""Offline evaluation harness for the SQL generator node.

Scope: this package evaluates only ``app.agents.sql_generator.sql_generator_node``.
It runs the node in isolation over a small golden dataset and scores the
generated SQL deterministically (execution accuracy against a reference query,
safety/validity, executability). An optional, flag-gated RAGAS
``LLMSQLEquivalence`` metric provides a semantic-equivalence signal but never
gates CI.
"""
