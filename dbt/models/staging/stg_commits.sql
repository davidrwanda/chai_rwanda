{{
    config(
        materialized='view',
        schema='staging'
    )
}}

WITH source AS (
    SELECT * FROM {{ source('raw', 'commits') }}
),

cleaned AS (
    SELECT
        -- Primary key
        commit_sha,
        
        -- Author information
        TRIM(author_name) AS author_name,
        LOWER(TRIM(author_email)) AS author_email,
        author_date,
        
        -- Committer information
        TRIM(committer_name) AS committer_name,
        LOWER(TRIM(committer_email)) AS committer_email,
        committer_date,
        
        -- Commit details
        TRIM(commit_message) AS commit_message,
        COALESCE(comment_count, 0) AS comment_count,
        
        -- Derived fields
        CASE 
            WHEN LOWER(commit_message) LIKE '%merge%' THEN TRUE
            ELSE FALSE
        END AS is_merge_commit,
        
        LENGTH(commit_message) AS message_length,
        
        -- Temporal features
        DATE(author_date) AS commit_date,
        EXTRACT(HOUR FROM author_date) AS commit_hour,
        EXTRACT(DOW FROM author_date) AS day_of_week,
        
        -- Metadata
        loaded_at,
        source
        
    FROM source
    WHERE commit_sha IS NOT NULL
        AND author_date IS NOT NULL
)

SELECT * FROM cleaned
