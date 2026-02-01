{{
    config(
        materialized='table',
        schema='analytics'
    )
}}

WITH commits AS (
    SELECT * FROM {{ ref('stg_commits') }}
),

-- Author-level aggregations
author_metrics AS (
    SELECT
        author_email,
        author_name,
        COUNT(*) AS total_commits,
        COUNT(CASE WHEN is_merge_commit THEN 1 END) AS merge_commits,
        AVG(message_length) AS avg_message_length,
        AVG(comment_count) AS avg_comments,
        MIN(author_date) AS first_commit_date,
        MAX(author_date) AS last_commit_date,
        COUNT(DISTINCT commit_date) AS active_days
    FROM commits
    GROUP BY author_email, author_name
),

-- Temporal patterns
temporal_metrics AS (
    SELECT
        commit_date,
        commit_hour,
        day_of_week,
        COUNT(*) AS commits_count,
        COUNT(CASE WHEN is_merge_commit THEN 1 END) AS merge_commits_count,
        AVG(message_length) AS avg_message_length,
        AVG(comment_count) AS avg_comments
    FROM commits
    GROUP BY commit_date, commit_hour, day_of_week
),

-- Enriched commit data
commit_metrics AS (
    SELECT
        c.*,
        a.total_commits AS author_total_commits,
        a.merge_commits AS author_merge_commits,
        a.avg_message_length AS author_avg_message_length,
        a.first_commit_date AS author_first_commit,
        a.last_commit_date AS author_last_commit,
        a.active_days AS author_active_days,
        
        -- Categorizations
        CASE
            WHEN c.commit_hour BETWEEN 9 AND 17 THEN 'business_hours'
            WHEN c.commit_hour BETWEEN 18 AND 23 THEN 'evening'
            ELSE 'night_early_morning'
        END AS time_category,
        
        CASE
            WHEN c.day_of_week IN (0, 6) THEN 'weekend'
            ELSE 'weekday'
        END AS day_category,
        
        CASE
            WHEN c.message_length < 50 THEN 'short'
            WHEN c.message_length < 200 THEN 'medium'
            ELSE 'long'
        END AS message_category,
        
        -- Engagement score (composite metric)
        (c.comment_count * 2.0) + 
        (CASE WHEN c.is_merge_commit THEN 1.0 ELSE 0.0 END) +
        (c.message_length / 100.0) AS engagement_score
        
    FROM commits c
    LEFT JOIN author_metrics a ON c.author_email = a.author_email
)

SELECT * FROM commit_metrics
