-- Aggregate origination anatomy. The query intentionally never selects loan_id.
WITH base AS (
    SELECT
        CASE
            WHEN is_relief_refinance IS TRUE THEN 'relief'
            WHEN is_relief_refinance IS FALSE THEN 'non_relief'
            ELSE 'unknown_relief'
        END AS segment,
        original_upb, classic_fico, original_ltv, original_dti, original_cltv,
        original_term, units, occupancy, loan_purpose, channel,
        property_type, first_time_homebuyer, amortization_type
    FROM dim_loan
), long AS (
    SELECT segment, 1 AS dimension_order, 'classic_fico' AS dimension,
        CASE
            WHEN classic_fico IS NULL OR classic_fico < 300 OR classic_fico > 850 THEN 'Unavailable'
            WHEN classic_fico < 620 THEN '<620'
            WHEN classic_fico < 680 THEN '620-679'
            WHEN classic_fico < 740 THEN '680-739'
            WHEN classic_fico < 780 THEN '740-779'
            ELSE '780+'
        END AS bucket, original_upb
    FROM base
    UNION ALL
    SELECT segment, 2, 'original_ltv',
        CASE
            WHEN original_ltv IS NULL OR original_ltv < 0 OR original_ltv > 200 THEN 'Unavailable'
            WHEN original_ltv <= 60 THEN '<=60'
            WHEN original_ltv <= 75 THEN '61-75'
            WHEN original_ltv <= 80 THEN '76-80'
            WHEN original_ltv <= 90 THEN '81-90'
            WHEN original_ltv <= 95 THEN '91-95'
            ELSE '96+'
        END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 3, 'original_dti',
        CASE
            WHEN original_dti IS NULL OR original_dti < 0 OR original_dti > 100 THEN 'Unavailable'
            WHEN original_dti <= 20 THEN '<=20'
            WHEN original_dti <= 30 THEN '21-30'
            WHEN original_dti <= 40 THEN '31-40'
            WHEN original_dti <= 50 THEN '41-50'
            ELSE '51+'
        END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 4, 'original_cltv',
        CASE
            WHEN original_cltv IS NULL OR original_cltv < 0 OR original_cltv > 250 THEN 'Unavailable'
            WHEN original_cltv <= 60 THEN '<=60'
            WHEN original_cltv <= 75 THEN '61-75'
            WHEN original_cltv <= 80 THEN '76-80'
            WHEN original_cltv <= 90 THEN '81-90'
            WHEN original_cltv <= 100 THEN '91-100'
            ELSE '101+'
        END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 5, 'original_upb',
        CASE
            WHEN original_upb IS NULL OR original_upb <= 0 THEN 'Unavailable'
            WHEN original_upb < 100000 THEN '<100k'
            WHEN original_upb < 200000 THEN '100k-199k'
            WHEN original_upb < 300000 THEN '200k-299k'
            WHEN original_upb < 500000 THEN '300k-499k'
            ELSE '500k+'
        END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 6, 'original_term',
        CASE
            WHEN original_term IS NULL OR original_term <= 0 OR original_term > 480 THEN 'Unavailable'
            WHEN original_term <= 180 THEN '<=180'
            WHEN original_term <= 240 THEN '181-240'
            WHEN original_term <= 360 THEN '241-360'
            ELSE '361-480'
        END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 7, 'units',
        CASE
            WHEN units IS NULL OR units <= 0 THEN 'Unavailable'
            WHEN units = 1 THEN '1'
            WHEN units = 2 THEN '2'
            WHEN units = 3 THEN '3'
            WHEN units = 4 THEN '4'
            ELSE '5+'
        END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 8, 'occupancy',
        CASE WHEN occupancy IN ('P','I','S') THEN occupancy ELSE 'Unknown' END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 9, 'loan_purpose',
        CASE WHEN loan_purpose IN ('P','C','N','R') THEN loan_purpose ELSE 'Unknown' END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 10, 'channel',
        CASE WHEN channel IN ('R','B','C','T') THEN channel ELSE 'Unknown' END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 11, 'property_type',
        CASE WHEN property_type IN ('CO','CP','PU','SF') THEN property_type ELSE 'Unknown' END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 12, 'first_time_homebuyer',
        CASE WHEN first_time_homebuyer IN ('Y','N') THEN first_time_homebuyer ELSE 'Unknown' END, original_upb
    FROM base
    UNION ALL
    SELECT segment, 13, 'amortization_type',
        CASE WHEN amortization_type IN ('FRM','ARM') THEN amortization_type ELSE 'Unknown' END, original_upb
    FROM base
), grouped AS (
    SELECT segment, dimension_order, dimension, bucket,
        COUNT(*) AS loans,
        COUNT(*) FILTER (WHERE original_upb IS NOT NULL AND original_upb > 0) AS known_upb_loans,
        COUNT(*) FILTER (WHERE original_upb IS NULL OR original_upb <= 0) AS missing_upb_loans,
        SUM(original_upb) FILTER (WHERE original_upb IS NOT NULL AND original_upb > 0) AS opening_upb
    FROM long
    GROUP BY ALL
)
SELECT segment, dimension_order, dimension, bucket, loans, known_upb_loans,
    missing_upb_loans, opening_upb,
    SUM(loans) OVER (PARTITION BY segment, dimension) AS segment_loans,
    SUM(known_upb_loans) OVER (PARTITION BY segment, dimension) AS segment_known_upb_loans,
    SUM(opening_upb) OVER (PARTITION BY segment, dimension) AS segment_opening_upb,
    loans::DOUBLE / NULLIF(SUM(loans) OVER (PARTITION BY segment, dimension), 0) AS count_share,
    opening_upb / NULLIF(SUM(opening_upb) OVER (PARTITION BY segment, dimension), 0) AS balance_share
FROM grouped
ORDER BY segment, dimension_order, bucket
