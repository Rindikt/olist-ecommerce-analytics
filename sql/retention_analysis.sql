WITH order_months AS (
            SELECT
                c.customer_unique_id,
                DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS order_month,
                DATE_TRUNC('month', MIN(o.order_purchase_timestamp) OVER(PARTITION BY c.customer_unique_id))::DATE AS cohort_month
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
        )
        SELECT
            cohort_month,
            (order_month - cohort_month) / 30 AS cohort_age,
            COUNT(DISTINCT customer_unique_id) AS active_customers
        FROM order_months
        GROUP BY 1, 2
        ORDER BY 1, 2;


SELECT
            c.customer_city,
            COUNT(DISTINCT c.customer_unique_id) AS total_customers,
            COUNT(DISTINCT CASE WHEN counts.order_count > 1 THEN c.customer_unique_id END) AS repeat_customers,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN counts.order_count > 1 THEN c.customer_unique_id END) / COUNT(DISTINCT c.customer_unique_id), 2) AS repeat_rate
        FROM customers c
        JOIN (
            SELECT
                customer_id,
                customer_unique_id
            FROM customers
        ) cust_map ON c.customer_unique_id = cust_map.customer_unique_id
        JOIN orders o ON cust_map.customer_id = o.customer_id
        JOIN (

            SELECT
                customer_unique_id,
                COUNT(order_id) as order_count
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            GROUP BY customer_unique_id
        ) counts ON c.customer_unique_id = counts.customer_unique_id
        GROUP BY c.customer_city
        HAVING COUNT(DISTINCT c.customer_unique_id) > 100
        ORDER BY repeat_rate DESC
        LIMIT 10;