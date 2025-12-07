CREATE OR REPLACE
VIEW `daily_build`.`v_latest_branches_coverage_results` AS
WITH coverage_execs AS (
    SELECT
        exec_id,
        ROW_NUMBER() OVER (ORDER BY exec_id DESC) AS rn
    FROM daily_build.executions
    WHERE build_type = 'coverage'
      AND exec_id < 203000000000000000
),
latest_exec AS (
    SELECT exec_id FROM coverage_execs WHERE rn = 1
),
previous_exec AS (
    SELECT exec_id FROM coverage_execs WHERE rn = 2
),
latest_rows AS (
    SELECT
        le.exec_id AS exec_id,
        cr.directory,
        cr.file_name,
        cr.lines_hit,
        cr.lines_total,
        cr.module,
        cr.owner
    FROM daily_build.coverage_results cr
    JOIN latest_exec le ON cr.exec_id = le.exec_id
),
previous_rows AS (
    SELECT
        pe.exec_id AS exec_id,
        cr.directory,
        cr.file_name,
        cr.lines_hit,
        cr.lines_total,
        cr.module,
        cr.owner
    FROM daily_build.coverage_results cr
    JOIN previous_exec pe ON cr.exec_id = pe.exec_id
),
combined AS (
    -- rows present in previous (with optional latest)
    SELECT
        pr.exec_id AS previous_exec_id,
        lr.exec_id AS latest_exec_id,
        pr.directory,
        pr.file_name,
        pr.lines_hit AS previous_hit,
        lr.lines_hit AS latest_hit,
        pr.lines_total AS previous_total,
        lr.lines_total AS latest_total,
        pr.module,
        pr.owner
    FROM previous_rows pr
    LEFT JOIN latest_rows lr
      ON pr.directory = lr.directory
     AND pr.file_name = lr.file_name
    UNION ALL
    -- rows present only in latest (no matching previous)
    SELECT
        pr.exec_id AS previous_exec_id,
        lr.exec_id AS latest_exec_id,
        lr.directory,
        lr.file_name,
        pr.lines_hit AS previous_hit,
        lr.lines_hit AS latest_hit,
        pr.lines_total AS previous_total,
        lr.lines_total AS latest_total,
        lr.module,
        lr.owner
    FROM latest_rows lr
    LEFT JOIN previous_rows pr
      ON pr.directory = lr.directory
     AND pr.file_name = lr.file_name
    WHERE pr.exec_id IS NULL
)
SELECT
    c.previous_exec_id,
    c.latest_exec_id,
    c.directory,
    c.file_name,
    c.previous_hit,
    c.latest_hit,
    c.previous_total,
    c.latest_total,
    CAST(c.previous_hit AS DECIMAL(18, 6)) / NULLIF(c.previous_total, 0) AS previous_coverage,
    CAST(c.latest_hit AS DECIMAL(18, 6)) / NULLIF(c.latest_total, 0) AS latest_coverage,
    CASE
        WHEN c.previous_exec_id IS NULL THEN 'error'
        WHEN c.previous_total > 0 AND CAST(c.previous_hit AS DECIMAL(18, 6)) / c.previous_total >= 0.8 THEN 'pass'
        WHEN c.previous_total > 0 THEN 'fail'
        ELSE 'unknown'
    END AS previous_status,
    CASE
        WHEN c.latest_exec_id IS NULL THEN 'error'
        WHEN c.latest_total > 0 AND CAST(c.latest_hit AS DECIMAL(18, 6)) / c.latest_total >= 0.8 THEN 'pass'
        WHEN c.latest_total > 0 THEN 'fail'
        ELSE 'unknown'
    END AS latest_status,
    CASE
        WHEN c.previous_exec_id IS NULL THEN 'error'
        WHEN c.previous_total > 0 THEN GREATEST(0, 0.8 * c.previous_total - c.previous_hit)
        ELSE NULL
    END AS previous_gap_to_target,
    CASE
        WHEN c.latest_exec_id IS NULL THEN 'error'
        WHEN c.latest_total > 0 THEN GREATEST(0, 0.8 * c.latest_total - c.latest_hit)
        ELSE NULL
    END AS latest_gap_to_target,
    CASE
        WHEN c.previous_exec_id IS NULL OR c.latest_exec_id IS NULL THEN NULL
        WHEN c.previous_total > 0 AND c.latest_total > 0 THEN
            (
                (CAST(c.previous_hit AS DECIMAL(18, 6)) / c.previous_total)
                - (CAST(c.latest_hit AS DECIMAL(18, 6)) / c.latest_total)
            ) * (c.previous_total + c.latest_total) / 2
        ELSE NULL
    END AS coverage_change,
    c.module,
    c.owner
FROM combined c;
