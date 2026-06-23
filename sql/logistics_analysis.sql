 WITH order_delivery_metrics AS (
        SELECT order_id,
        	   order_purchase_timestamp,
        	   order_delivered_customer_date,
        	   EXTRACT(DAY FROM (order_delivered_customer_date - order_purchase_timestamp)) AS delivery_days,
        	   DATE_TRUNC('month', order_purchase_timestamp)::DATE AS month
        FROM orders
        WHERE order_delivered_customer_date IS NOT NULL
        )

        SELECT month,
               COUNT(order_id) AS total_orders,
        	   ROUND(AVG(delivery_days),2) AS avg_delivery_days,
        	   PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY delivery_days) AS p90_delivery_days,
        	   MAX(delivery_days) AS max_delivery_days,
               SUM(CASE WHEN delivery_days > 30 THEN 1 ELSE 0 END) AS late_orders_count
        FROM order_delivery_metrics
        GROUP BY month
        ORDER BY month