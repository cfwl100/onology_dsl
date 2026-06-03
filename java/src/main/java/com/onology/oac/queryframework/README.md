# OAC Query Framework

This package provides an extensible ontology query conversion framework for OAC.

## Main pipeline

1. Parse canonical OQL JSON into domain models.
2. Validate operation constraints, aliases, returns, conditions and aggregateFilter.
3. Resolve ontology objects, properties and relationships to physical bindings.
4. Build BindingGraph and select split strategy.
5. Build physical source fragments.
6. Translate source fragments through datasource translators.
7. Execute physical queries through datasource executors.
8. Assemble ontology objects, relationships or grouped metric rows.

## Key packages

- `domain`: OQL, metadata, binding graph, plan and result models.
- `core`: validator, binding resolver, split strategy selector and physical plan builder.
- `spi`: translator and executor extension interfaces.
- `registry`: extension lookup registry.
- `executor`: fragment execution engine.
- `assembler`: result assembly helpers.

## Extension points

To add a new datasource:

1. Add a `QueryTranslator` implementation.
2. Add a `DatasourceExecutor` implementation.
3. Register `DatasourceCapability` for the datasource.
4. Provide `PropertyBinding` and `RelationshipBinding` metadata.

To add a new function:

1. Register the function in a function registry.
2. Declare where it can appear.
3. Declare pushdown mapping or fallback execution behavior.

## Split strategy

`SplitStrategySelector` decides between:

- single-source single-table pushdown;
- single-source join pushdown;
- cross-source query plus OAC merge;
- graph relationship pushdown;
- relational association join;
- multi-stage association assembly;
- aggregate pushdown;
- partial aggregate merge;
- in-memory aggregate processing.

## Notes

The framework is currently isolated from the existing `/oac/{mode}` runtime path. It can be wired into explain mode first, then promoted to execute mode after concrete SQL, GQL, API, DAC and ES translators are implemented and tested.
