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
        cr.branches_hit,
        cr.branches_total,
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
        cr.branches_hit,
        cr.branches_total,
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
        pr.branches_hit AS previous_hit,
        lr.branches_hit AS latest_hit,
        pr.branches_total AS previous_total,
        lr.branches_total AS latest_total,
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
        pr.branches_hit AS previous_hit,
        lr.branches_hit AS latest_hit,
        pr.branches_total AS previous_total,
        lr.branches_total AS latest_total,
        lr.module,
        lr.owner
    FROM latest_rows lr
    LEFT JOIN previous_rows pr
      ON pr.directory = lr.directory
     AND pr.file_name = lr.file_name
    WHERE pr.exec_id IS NULL
),
computed AS (
    SELECT
        c.*,
        CAST(
            CASE
                WHEN c.previous_total IS NULL OR c.previous_total = 0 THEN NULL
                ELSE CAST(c.previous_hit AS DECIMAL(38, 10)) / c.previous_total
            END AS DECIMAL(11, 10)
        ) AS previous_coverage,
        CAST(
            CASE
                WHEN c.latest_total IS NULL OR c.latest_total = 0 THEN NULL
                ELSE CAST(c.latest_hit AS DECIMAL(38, 10)) / c.latest_total
            END AS DECIMAL(11, 10)
        ) AS latest_coverage,
        CAST(
            CASE
                WHEN SUM(c.previous_total) OVER () = 0 OR c.previous_hit IS NULL THEN NULL
                ELSE CAST(c.previous_hit AS DECIMAL(38, 10)) / SUM(c.previous_total) OVER ()
            END AS DECIMAL(11, 10)
        ) AS previous_weight,
        CAST(
            CASE
                WHEN SUM(c.latest_total) OVER () = 0 OR c.latest_total IS NULL THEN NULL
                ELSE CAST(c.latest_total AS DECIMAL(38, 10)) / SUM(c.latest_total) OVER ()
            END AS DECIMAL(11, 10)
        ) AS latest_weight,
        CAST(
            CASE
                WHEN SUM(COALESCE(c.latest_total, 0) + COALESCE(c.previous_total, 0)) OVER () = 0
                     OR (c.latest_total IS NULL AND c.previous_total IS NULL) THEN NULL
                ELSE CAST(
                    COALESCE(c.latest_total, 0) + COALESCE(c.previous_total, 0)
                    AS DECIMAL(38, 10)
                ) / SUM(COALESCE(c.latest_total, 0) + COALESCE(c.previous_total, 0)) OVER ()
            END AS DECIMAL(11, 10)
        ) AS combined_weight
    FROM combined c
)
SELECT
    d.previous_exec_id,
    d.latest_exec_id,
    d.directory,
    d.file_name,
    d.previous_hit,
    d.latest_hit,
    d.previous_total,
    d.latest_total,
    d.previous_coverage,
    d.latest_coverage,
    CAST(
        CASE
            WHEN d.previous_total IS NULL OR d.previous_hit IS NULL THEN NULL
            ELSE GREATEST(0, 0.8 * d.previous_total - d.previous_hit)
        END AS DECIMAL(18, 6)
    ) AS previous_gap_hit_to_80,
    CAST(
        CASE
            WHEN d.latest_total IS NULL OR d.latest_hit IS NULL THEN NULL
            ELSE GREATEST(0, 0.8 * d.latest_total - d.latest_hit)
        END AS DECIMAL(18, 6)
    ) AS latest_gap_hit_to_80,
    d.previous_weight,
    d.latest_weight,
    d.combined_weight,
    (
        CAST(
            CASE
                WHEN d.previous_exec_id IS NULL
                     OR d.latest_exec_id IS NULL
                     OR d.directory IS NULL OR d.directory = ''
                     OR d.file_name IS NULL OR d.file_name = ''
                     OR (d.previous_total IS NOT NULL AND d.previous_hit IS NOT NULL AND d.previous_total < d.previous_hit)
                     OR (d.latest_total IS NOT NULL AND d.latest_hit IS NOT NULL AND d.latest_total < d.latest_hit)
                    THEN 'error'
                WHEN d.previous_total > 0 AND d.previous_coverage >= 0.8 THEN 'pass'
                WHEN d.previous_total > 0 THEN 'fail'
                ELSE 'unknown'
            END AS CHAR CHARACTER SET utf8mb4
        ) COLLATE utf8mb4_unicode_ci
    ) AS previous_status,
    (
        CAST(
            CASE
                WHEN d.previous_exec_id IS NULL
                     OR d.latest_exec_id IS NULL
                     OR d.directory IS NULL OR d.directory = ''
                     OR d.file_name IS NULL OR d.file_name = ''
                     OR (d.previous_total IS NOT NULL AND d.previous_hit IS NOT NULL AND d.previous_total < d.previous_hit)
                     OR (d.latest_total IS NOT NULL AND d.latest_hit IS NOT NULL AND d.latest_total < d.latest_hit)
                    THEN 'error'
                WHEN d.latest_total > 0 AND d.latest_coverage >= 0.8 THEN 'pass'
                WHEN d.latest_total > 0 THEN 'fail'
                ELSE 'unknown'
            END AS CHAR CHARACTER SET utf8mb4
        ) COLLATE utf8mb4_unicode_ci
    ) AS latest_status,
    CAST(
        CASE
            WHEN d.previous_coverage IS NULL OR d.latest_coverage IS NULL THEN NULL
            ELSE d.latest_coverage - d.previous_coverage
        END AS DECIMAL(11, 10)
    ) AS diff_coverage,
    d.module,
    d.owner
FROM computed d;
