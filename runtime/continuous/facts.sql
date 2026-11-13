CREATE TABLE continuous_facts_v1
(
    run_id String,
    output_partition UInt16,
    output_offset UInt64,
    kind LowCardinality(String),
    fact_json String
)
ENGINE = MergeTree
ORDER BY (run_id, output_partition, output_offset);
