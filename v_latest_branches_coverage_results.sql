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
)
SELECT
    pr.exec_id AS previous_exec_id,
    lr.exec_id AS latest_exec_id,
    pr.directory,
    pr.file_name,
    pr.lines_hit AS previous_hit,
    lr.lines_hit AS latest_hit,
    pr.lines_total AS previous_total,
    lr.lines_total AS latest_total,
    CAST(pr.lines_hit AS DECIMAL(18, 6)) / NULLIF(pr.lines_total, 0) AS previous_coverage,
    CAST(lr.lines_hit AS DECIMAL(18, 6)) / NULLIF(lr.lines_total, 0) AS latest_coverage,
    CASE
        WHEN pr.lines_total > 0 AND CAST(pr.lines_hit AS DECIMAL(18, 6)) / pr.lines_total >= 0.8 THEN 'pass'
        WHEN pr.lines_total > 0 THEN 'fail'
        ELSE 'unknown'
    END AS previous_status,
    CASE
        WHEN lr.lines_total > 0 AND CAST(lr.lines_hit AS DECIMAL(18, 6)) / lr.lines_total >= 0.8 THEN 'pass'
        WHEN lr.lines_total > 0 THEN 'fail'
        ELSE 'unknown'
    END AS latest_status,
    CASE
        WHEN pr.lines_total > 0 THEN GREATEST(0, 0.8 * pr.lines_total - pr.lines_hit)
        ELSE NULL
    END AS previous_gap_to_target,
    CASE
        WHEN lr.lines_total > 0 THEN GREATEST(0, 0.8 * lr.lines_total - lr.lines_hit)
        ELSE NULL
    END AS latest_gap_to_target,
    CASE
        WHEN pr.lines_total > 0 AND lr.lines_total > 0 THEN
            (
                (CAST(pr.lines_hit AS DECIMAL(18, 6)) / pr.lines_total)
                - (CAST(lr.lines_hit AS DECIMAL(18, 6)) / lr.lines_total)
            ) * (pr.lines_total + lr.lines_total) / 2
        ELSE NULL
    END AS coverage_change,
    lr.module,
    lr.owner
FROM previous_rows pr
JOIN latest_rows lr
  ON pr.directory = lr.directory
 AND pr.file_name = lr.file_name;
