import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
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
    return pd.read_sql(query, get_engine())

st.set_page_config(page_title="Olist Analytics", layout="wide")
st.title("📊 Аналитический дашборд: Olist E-commerce")

tab1, tab2, tab3 = st.tabs(["Финансы", "Логистика", "Клиенты (Retention)"])

with tab1:
    @st.cache_data
    def load_revenue_data():
        # Забираем чистые данные из таблиц
        query = """
        SELECT 
            o.order_purchase_timestamp,
            c.customer_city,
            oi.price + oi.freight_value AS order_value
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        """
        df = get_data(query)

        # Приводим типы и считаем месяц
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
        df['month_order'] = df['order_purchase_timestamp'].dt.to_period('M').dt.to_timestamp()

        # Агрегация данных
        monthly_stats = df.groupby(['month_order', 'customer_city']).agg(
            total_revenue=('order_value', 'sum'),
            avg_order_value=('order_value', 'mean')
        ).reset_index()

        # Фильтр топ-5 городов по общей выручке
        top_cities = monthly_stats.groupby('customer_city')['total_revenue'].sum().nlargest(5).index
        df_filtered = monthly_stats[monthly_stats['customer_city'].isin(top_cities)]

        # Подготовка данных для визуализации (pivot)
        pivot_revenue = df_filtered.pivot(index='month_order', columns='customer_city', values='total_revenue')
        pivot_avg = df_filtered.pivot(index='month_order', columns='customer_city', values='avg_order_value')

        # Убираем последний неполный месяц, если нужно
        return pivot_revenue.iloc[:-1], pivot_avg.iloc[:-1]

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
        # Забираем только необходимые сырые данные без SQL-агрегатов
        query = """
        SELECT order_id, order_purchase_timestamp, order_delivered_customer_date 
        FROM orders 
        WHERE order_delivered_customer_date IS NOT NULL
        """
        df = get_data(query)

        # Приводим к формату дат
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
        df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'])

        # Считаем разницу в днях
        df['delivery_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.days
        # Создаем колонку месяца
        df['month'] = df['order_purchase_timestamp'].dt.to_period('M').dt.to_timestamp()

        # Агрегируем данные (аналог твоего SQL запроса)
        report = df.groupby('month').agg(
            total_orders=('order_id', 'count'),
            avg_delivery_days=('delivery_days', 'mean'),
            p90_delivery_days=('delivery_days', lambda x: x.quantile(0.9)),
            max_delivery_days=('delivery_days', 'max'),
            late_orders_count=('delivery_days', lambda x: (x > 30).sum())
        ).reset_index()

        return report.sort_values('month')

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
                * **Эффективность логистики:** Начиная с марта, наблюдается устойчивое снижение времени доставки (среднее и P90). Это произошло на фоне выхода общего объема заказов на «плато», что говорит о достижении системой оптимального рабочего ритма.
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
        # Забираем только сырые данные
        query = """
        SELECT c.customer_unique_id, o.order_purchase_timestamp
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        """
        df = get_data(query)
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
        df['month'] = df['order_purchase_timestamp'].dt.to_period('M')

        # Определяем месяц первой покупки для каждого клиента
        df['cohort'] = df.groupby('customer_unique_id')['month'].transform('min')

        # Считаем возраст когорты
        df['cohort_age'] = (df['month'] - df['cohort']).apply(lambda x: x.n)

        # Считаем активных клиентов
        cohort_df = df.groupby(['cohort', 'cohort_age'])['customer_unique_id'].nunique().reset_index()
        pivot = cohort_df.pivot(index='cohort', columns='cohort_age', values='customer_unique_id')

        # Считаем Retention
        pivot_pct = pivot.divide(pivot.iloc[:, 0], axis=0)
        return pivot_pct.drop(columns=[0]).iloc[3:-2]

    @st.cache_data
    def load_cities_loyalty():
        # Упрощенный запрос для получения данных по городам
        query_cities = """
        SELECT c.customer_city, c.customer_unique_id, o.order_id
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        """
        df = get_data(query_cities)

        # Считаем заказы на клиента и всего на город в Pandas
        cust_counts = df.groupby('customer_unique_id')['order_id'].count()
        df = df.merge(cust_counts.rename('order_count'), on='customer_unique_id')

        city_stats = df.groupby('customer_city').agg(
            total_customers=('customer_unique_id', 'nunique'),
            repeat_customers=('customer_unique_id', lambda x: x[df.loc[x.index, 'order_count'] > 1].nunique())
        )

        city_stats = city_stats[city_stats['total_customers'] > 100].copy()
        city_stats['repeat_rate'] = (city_stats['repeat_customers'] / city_stats['total_customers']) * 100
        return city_stats.sort_values('repeat_rate', ascending=False).head(10)

    try:
        data = load_cohort_data()
        result_cities = load_cities_loyalty()

        col1, col2 = st.columns([4, 1])

        with col1:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.heatmap(data, annot=True, fmt='.1%', cmap='YlGnBu', annot_kws={"size": 7}, ax=ax)
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
                * **Стабильность базы:** Отсутствие резких провалов или «взрывов» лояльности в когортах указывает на то, что текущие операционные показатели стабильны, но не стимулируют повторные покупки.
                * **География лояльности:** Анализ повторных покупок в разрезе городов показал наличие устойчивых региональных различий. В городах-лидерах Retention-rate достигает ~3.5–3.8% (при среднем по компании ~3.1%). Это указывает на то, что лояльность не распределена равномерно и может зависеть от качества локальной логистической инфраструктуры. Рекомендуется провести дополнительное исследование этих регионов для масштабирования успешных логистических практик на всю сеть.
                * **Стратегический фокус:** Стратегия роста компании должна фокусироваться на эффективности каналов привлечения (CAC) и работе с ассортиментом, так как полагаться на органический возврат текущей базы при текущих показателях недостаточно для агрессивного роста выручки.
                """)

    except Exception as e:
        st.error(f"Ошибка при обработке данных: {e}")