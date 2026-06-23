WITH order_totals AS (
            -- Сначала считаем сумму по каждому заказу (это наш честный "чек")
            SELECT order_id,
                   SUM(price + freight_value) AS order_value
            FROM order_items
            GROUP BY order_id
        ),
        monthly_stats AS (
            SELECT
                DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS month_order,
                c.customer_city,
                COUNT(o.order_id) AS total_orders,
                SUM(ot.order_value) AS total_revenue,
                ROUND(AVG(ot.order_value),2) AS avg_order_value -- А теперь считаем среднее от чеков!
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN order_totals ot ON o.order_id = ot.order_id
            GROUP BY 1, 2
        ),
        top_cities AS (
            -- Возвращаем фильтр по выручке
            SELECT customer_city
            FROM monthly_stats
            GROUP BY customer_city
            ORDER BY SUM(total_revenue) DESC
            LIMIT 5
        )
        SELECT * FROM monthly_stats
        WHERE customer_city IN (SELECT customer_city FROM top_cities)
        ORDER BY 1, 2;