import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

from db_utils import get_engine


def get_data(query):
    engine = get_engine()
    return pd.read_sql(query, engine)

st.set_page_config(page_title="Olist Analytics", layout="wide")
st.title("📊 Аналитический дашборд: Olist E-commerce")

tab1, tab2, tab3 = st.tabs(["Финансы", "Логистика", "Клиенты (Retention)"])

with tab1:
    @st.cache_data
    def load_revenue_data():
        my_query = """
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
        """
        df = get_data(my_query)
        pivot_revenue = df.pivot(index='month_order', columns='customer_city', values='total_revenue')
        pivot_avg = df.pivot(index='month_order', columns='customer_city', values='avg_order_value')
        pivot_revenue = pivot_revenue.iloc[:-1]
        pivot_avg = pivot_avg.iloc[:-1]
        return pivot_revenue, pivot_avg


    st.header("Финансовые показатели")

    try:
        pivot_revenue, pivot_avg = load_revenue_data()
        total_revenue = pivot_revenue.sum(axis=1)
        avg_check = pivot_avg.mean(axis=1)

        col_graph, col_stats = st.columns([4, 1])

        with col_graph:
            fig, ax1 = plt.subplots(figsize=(10, 5))

            total_revenue.plot(kind='bar', ax=ax1, color='skyblue', alpha=0.7, label='Выручка')
            ax1.set_ylabel('Выручка (BRL)', color='blue')

            ax2 = ax1.twinx()
            avg_check.plot(kind='line', ax=ax2, color='darkred', marker='o', linewidth=2, label='Средний чек')
            ax2.set_ylabel('Средний чек (BRL)', color='darkred')

            plt.title('Динамика выручки и среднего чека')
            st.pyplot(fig)

        with col_stats:
            rev_delta = ((total_revenue.iloc[-1] - total_revenue.iloc[-2]) / total_revenue.iloc[-2]) * 100
            aov_delta = ((avg_check.iloc[-1] - avg_check.iloc[-2]) / avg_check.iloc[-2]) * 100

            st.metric("Выручка (последний мес.)", f"{total_revenue.iloc[-1]:,.0f} BRL", f"{rev_delta:.1f}%")
            st.metric("Средний чек", f"{avg_check.iloc[-1]:,.2f} BRL", f"{aov_delta:.1f}%")

            st.write("---")
            st.caption("Показатели отображают динамику последнего отчетного месяца к предыдущему.")

        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.write("### Средний чек по городам")
            styled_table = pivot_avg.style.format("{:.2f} BRL") \
                .background_gradient(cmap='Greens', axis=0)
            st.dataframe(styled_table, use_container_width=False, height=810)

        st.subheader("📝 Итоговые выводы по финансам")
        with st.expander("Показать подробный анализ"):
            st.markdown("""
                * **Сезонный пик:** Выявлен выраженный всплеск активности в ноябре, характерный для ритейл-сектора (период распродаж).
                * **Концентрация спроса:**  Города-лидеры (особенно Сан-Паулу) демонстрируют высокую степень корреляции между ростом заказов и выручкой, что подтверждает устойчивость данного сегмента.
                * **Декабрьская просадка:** Наблюдается снижение активности в декабре, что может быть связано с исчерпанием спроса после ноябрьских промо-акций.
                * **Рекомендация:** Для нивелирования декабрьского спада целесообразно рассмотреть запуск программы удержания (retention) или дополнительные маркетинговые коммуникации в начале декабря.
                """)


    except Exception as e:
        st.error(f"Ошибка при обработке данных: {e}")


with tab2:
    st.header("Анализ логистики")
    @st.cache_data
    def load_logistics_data():
        my_query = """
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
        """
        return get_data(my_query)

    try:
        df = load_logistics_data()
        df['share_late_orders'] = round(df.late_orders_count / df.total_orders * 100, 2)
        df_plot = df.iloc[2:-1]

        col_main, col_sidebar = st.columns([3, 1])

        with col_main:
            fig1, ax1 = plt.subplots(figsize=(10, 4))
            ax1.bar(df_plot['month'], df_plot['total_orders'], color='#E0E0E0', width=15, label='Заказы')
            ax2 = ax1.twinx()
            ax2.plot(df_plot['month'], df_plot['p90_delivery_days'], color='red', marker='o', label='P90 доставки')
            ax2.plot(df_plot['month'], df_plot['avg_delivery_days'], color='blue', linestyle='--', label='Среднее')
            ax1.set_title('Логистика: Зависимость качества от нагрузки')
            ax1.legend(loc='upper left'); ax2.legend(loc='upper right')

            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            plt.xticks(rotation=45)

            st.pyplot(fig1)

            col_graph_2, col_insights_2 = st.columns([3, 1])

            with col_graph_2:
                fig2, ax3 = plt.subplots(figsize=(8, 3))
                ax3.fill_between(df_plot['month'], df_plot['share_late_orders'], color='salmon', alpha=0.3)
                ax3.plot(df_plot['month'], df_plot['share_late_orders'], color='darkred', marker='o', linewidth=2)
                ax3.axhline(y=2.5, color='green', linestyle='--', label='Цель (2.5%)')
                ax3.set_title('Доля некачественных доставок (> 30 дней)')
                ax3.legend()

                ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                fig2.autofmt_xdate(rotation=45)

                st.pyplot(fig2)

            with col_insights_2:
                st.subheader("💡 Аналитика")
                worst = df_plot.loc[df_plot['share_late_orders'].idxmax()]
                st.markdown(f"""
                * **Пик:** {worst['month'].strftime('%b %Y')} ({worst['share_late_orders']}%).
                * **Аудит:** Уровень выше 2.5% требует проверки партнеров.
                * **Риск:** Проблемы масштабирования сети.
                """)

        with col_sidebar:
            st.subheader("KPI (последний мес.)")
            curr = df.iloc[-2]
            prev = df.iloc[-3]

            avg_delta = ((curr['avg_delivery_days'] - prev['avg_delivery_days']) / prev['avg_delivery_days']) * 100
            p90_delta = ((curr['p90_delivery_days'] - prev['p90_delivery_days']) / prev['p90_delivery_days']) * 100

            st.metric("Avg доставка", f"{curr['avg_delivery_days']:.1f} дн.", f"{avg_delta:.1f}%", delta_color="inverse")
            st.metric("P90 доставки", f"{curr['p90_delivery_days']:.1f} дн.", f"{p90_delta:.1f}%", delta_color="inverse")
            st.metric("Просрочки > 30д", f"{curr['share_late_orders']:.1f}%")

        st.divider()
        st.subheader("📝 Итоговые выводы по логистике")
        with st.expander("Показать подробный анализ"):
            st.markdown("""
                * **Качество данных:** Первые два месяца характеризуются низкой статистической значимостью (единичные заказы), что создает аномальные пики на графике. Эти данные были приняты к сведению, но не учитываются при формировании выводов о стабильности системы.
                * **Эффективность логистики:**  Начиная с марта, наблюдается устойчивое снижение времени доставки (среднее и P90). Это произошло на фоне выхода общего объема заказов на «плато», что говорит о достижении системой оптимального рабочего ритма.
                * **Анализ критических задержек:** Исследование доли заказов со сроком доставки > 30 дней выявило «период турбулентности» (октябрь 2017 – март 2018). В этот промежуток доля «долгих» доставок была значительно выше целевого уровня в 2.5%, что стало следствием резкого роста нагрузки.
                * **Результат оптимизации:** К апрелю 2018 года компании удалось вернуть долю критических задержек к историческому минимуму (~2.5%).
                * **Управленческий инсайт:** Система демонстрирует высокую реактивность. После периода операционного стресса конца 2017 года, логистическая сеть была успешно адаптирована под текущие объемы. Рост нагрузки более не приводит к «взрывному» росту времени доставки, что подтверждает эффективность принятых мер по управлению цепочкой поставок.
                """)

    except Exception as e:
        st.error(f"Ошибка: {e}")

with tab3:
    st.header("Когортный анализ")

    @st.cache_data
    def load_cohort_data():
        my_query = """
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
        """
        df = get_data(my_query)

        pivot = df.pivot(index='cohort_month', columns='cohort_age', values='active_customers')

        pivot_pct = pivot.divide(pivot.iloc[:, 0], axis=0)
        cohort_pivot_clean = pivot_pct.drop(columns=[0]).iloc[3:-2]
        return cohort_pivot_clean

    @st.cache_data
    def load_cities_loyalty():
        query_cities = """
        SELECT 
            c.customer_city,
            COUNT(DISTINCT c.customer_unique_id) AS total_customers,
            COUNT(DISTINCT CASE WHEN counts.order_count > 1 THEN c.customer_unique_id END) AS repeat_customers,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN counts.order_count > 1 THEN c.customer_unique_id END) / COUNT(DISTINCT c.customer_unique_id), 2) AS repeat_rate
        FROM customers c
        JOIN (
            -- Сначала считаем заказы на каждого уникального клиента
            SELECT 
                customer_id, 
                customer_unique_id 
            FROM customers
        ) cust_map ON c.customer_unique_id = cust_map.customer_unique_id
        JOIN orders o ON cust_map.customer_id = o.customer_id
        JOIN (
            -- Подзапрос для определения количества заказов на клиента
            SELECT 
                customer_unique_id, 
                COUNT(order_id) as order_count 
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            GROUP BY customer_unique_id
        ) counts ON c.customer_unique_id = counts.customer_unique_id
        GROUP BY c.customer_city
        HAVING COUNT(DISTINCT c.customer_unique_id) > 100 -- фильтр городов по репрезентативности
        ORDER BY repeat_rate DESC
        LIMIT 10;
        """
        return get_data(query_cities)

    try:
        data = load_cohort_data()
        result_cities = load_cities_loyalty()

        col1, col2 = st.columns([4, 1])

        with col1:
            fig, ax = plt.subplots(figsize=(10, 6))

            sns.heatmap(data, annot=True, fmt='.1%', cmap='YlGnBu',
                        annot_kws={"size": 7}, ax=ax)
            st.pyplot(fig)
            st.write("### Топ городов по лояльности")
            styled_df = result_cities.style.format({
                'repeat_rate': '{:.2f}%',
                'total_customers': '{:.0f}',
                'repeat_customers': '{:.0f}'
            }).background_gradient(subset=['repeat_rate'], cmap='YlGnBu')
            st.dataframe(styled_df, use_container_width=True)

        with col2:
            st.write("### Выводы")
            st.markdown("""
                * **Низкий Retention (~0.5%):** Площадка транзакционная.
                * **Стабильность:** Резких оттоков нет.
                * **Регионы:** Есть потенциал в городах-лидерах.
                """)
        st.divider()
        st.subheader("📝 Итоговые выводы по клиентам")

        with st.expander("Показать подробный анализ"):
            st.markdown("""
                * **Низкий Retention (~0.5%):** Площадка носит транзакционный характер. Пользователи приходят за конкретным товаром, а не за брендом.
                * **Стабильность базы:**  Отсутствие резких провалов или «взрывов» лояльности в когортах указывает на то, что текущие операционные показатели стабильны, но не стимулируют повторные покупки.
                * **География лояльности:** Анализ повторных покупок в разрезе городов показал наличие устойчивых региональных различий. В городах-лидерах Retention-rate достигает ~3.5–3.8% (при среднем по компании ~3.1%). Это указывает на то, что лояльность не распределена равномерно и может зависеть от качества локальной логистической инфраструктуры. Рекомендуется провести дополнительное исследование этих регионов для масштабирования успешных логистических практик на всю сеть.
                * **Стратегический фокус:** Стратегия роста компании должна фокусироваться на эффективности каналов привлечения (CAC) и работе с ассортиментом, так как полагаться на органический возврат текущей базы при текущих показателях недостаточно для агрессивного роста выручки.
                """)

    except Exception as e:
        st.error(f"Ошибка при обработке данных: {e}")