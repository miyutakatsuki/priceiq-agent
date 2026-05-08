"""PriceIQ Tool 1 — query_sales_data over Olist SQLite.

Data: Olist Brazilian E-Commerce dataset (Kaggle slug
`terencicp/e-commerce-dataset-by-olist-as-an-sqlite-database`).
11 tables · ~100K delivered orders 2016-10 to 2018-08 · 71 product categories
(Portuguese ↔ English translation table).

Public API:
    list_categories(min_orders=100) -> list[{pt, en, n_orders}]
    query_sales_data(category, start_date=None, end_date=None) -> dict
        Returns price stats + monthly_panel (used by Tools 2/3/5).

Token (KAGGLE_API_TOKEN, format `KGAT_...`):
    Colab → userdata.get('KAGGLE_API_TOKEN') (set in Secrets panel)
    Local → export KAGGLE_API_TOKEN=KGAT_xxx
"""

import os
import sqlite3
from typing import Optional

_DATASET = "terencicp/e-commerce-dataset-by-olist-as-an-sqlite-database"

# 模块级缓存（避免重复下载 / 重复 JOIN translation 表）
_db_path = None
_trans = None


def _ensure_db() -> str:
    """Lazy-download Olist SQLite (~110MB) and cache the path module-globally.

    First call: kagglehub fetches to ~/.cache/kagglehub (Colab) or local cache.
    Subsequent calls within the same process: returns cached `_db_path` for free.
    Cross-process caching is handled by kagglehub itself.
    """
    global _db_path
    if _db_path and os.path.exists(_db_path):
        return _db_path

    import kagglehub
    folder = kagglehub.dataset_download(_DATASET)
    for f in os.listdir(folder):
        if f.endswith(".sqlite"):
            _db_path = os.path.join(folder, f)
            return _db_path
    raise FileNotFoundError(f"No .sqlite file in {folder}")


def _translation() -> dict:
    """Portuguese → English category mapping (71 entries from Olist).

    Cached module-globally on first call. The translation table is small (71 rows)
    and immutable, so we hold the entire dict in memory rather than re-querying.
    """
    global _trans
    if _trans is not None:
        return _trans
    with sqlite3.connect(_ensure_db()) as conn:
        rows = conn.execute(
            "SELECT product_category_name, product_category_name_english "
            "FROM product_category_name_translation"
        ).fetchall()
    _trans = dict(rows)
    return _trans


def list_categories(min_orders: int = 100) -> list:
    """List Olist categories with ≥ min_orders delivered orders.

    Default min_orders=100 returns ~50/71 categories (excludes long-tail
    categories with too few orders for any meaningful elasticity estimate).
    Pass `min_orders=500` to get the top ~10 high-volume categories only.

    Returns: [{"pt": ..., "en": ..., "n_orders": ...}, ...] ranked desc by n_orders.
    """
    # Categories ranked by delivered-order volume; only categories with
    # ≥ min_orders are returned (filters noise from low-volume tail).
    sql = """
        SELECT p.product_category_name AS pt, COUNT(*) AS n
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE p.product_category_name IS NOT NULL
          AND o.order_status = 'delivered'
        GROUP BY p.product_category_name
        HAVING n >= ?
        ORDER BY n DESC
    """
    with sqlite3.connect(_ensure_db()) as conn:
        rows = conn.execute(sql, (min_orders,)).fetchall()
    trans = _translation()
    return [{"pt": pt, "en": trans.get(pt, pt), "n_orders": n} for pt, n in rows]


def query_sales_data(category: str,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> dict:
    """查询某品类的销售数据。

    Args:
        category: Olist 葡语品类名（如 'esporte_lazer'）
        start_date: ISO 日期 'YYYY-MM-DD'，None = 不限
        end_date: 同上

    Returns:
        dict 含 summary 统计 + monthly_panel（给 Tool 2 OLS 用）。
        无数据时 found=False。
    """
    # Only count `delivered` orders (Olist statuses include canceled,
    # unavailable, invoiced, shipped, etc.). For elasticity we want fulfilled
    # demand at the price point, not order intent. Excludes ~3% of records.
    where = ["p.product_category_name = ?", "o.order_status = 'delivered'"]
    params = [category]
    if start_date:
        where.append("o.order_purchase_timestamp >= ?")
        params.append(start_date)
    if end_date:
        where.append("o.order_purchase_timestamp <= ?")
        params.append(end_date)
    where_sql = " AND ".join(where)

    # 1) Aggregate summary (counts, price min/max/mean, freight mean, date range)
    summary_sql = f"""
        SELECT
            COUNT(*) AS n_orders,
            COUNT(DISTINCT o.order_id) AS n_unique_orders,
            MIN(oi.price) AS p_min,
            MAX(oi.price) AS p_max,
            AVG(oi.price) AS p_mean,
            AVG(oi.freight_value) AS f_mean,
            MIN(o.order_purchase_timestamp) AS d_min,
            MAX(o.order_purchase_timestamp) AS d_max
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE {where_sql}
    """

    # 2) Monthly panel (input to Tool 2 OLS + Tool 3 seasonality)
    panel_sql = f"""
        SELECT
            strftime('%Y-%m', o.order_purchase_timestamp) AS month,
            COUNT(*) AS n_orders,
            AVG(oi.price) AS avg_price,
            AVG(oi.freight_value) AS avg_freight,
            AVG(COALESCE(op.payment_installments, 1.0)) AS avg_installments
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN order_payments op ON oi.order_id = op.order_id
        WHERE {where_sql}
        GROUP BY month
        ORDER BY month
    """

    # 3) Sorted prices for median (Python computes median from this list)
    median_sql = f"""
        SELECT oi.price FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE {where_sql}
        ORDER BY oi.price
    """

    with sqlite3.connect(_ensure_db()) as conn:
        conn.row_factory = sqlite3.Row
        s = conn.execute(summary_sql, params).fetchone()
        if not s or s['n_orders'] == 0:
            return {"category": category, "found": False,
                    "message": f"No delivered orders for '{category}'"}
        panel = [dict(r) for r in conn.execute(panel_sql, params).fetchall()]
        prices = [r[0] for r in conn.execute(median_sql, params).fetchall()]

    median = prices[len(prices) // 2] if prices else 0.0

    return {
        "category": category,
        "category_english": _translation().get(category, category),
        "found": True,
        "n_orders": s['n_orders'],
        "n_unique_orders": s['n_unique_orders'],
        "date_range": [s['d_min'][:10], s['d_max'][:10]],
        "price_stats": {
            "min": round(s['p_min'], 2),
            "max": round(s['p_max'], 2),
            "mean": round(s['p_mean'], 2),
            "median": round(median, 2),
        },
        "freight_mean": round(s['f_mean'], 2),
        "monthly_panel": [
            {
                "month": r['month'],
                "n_orders": r['n_orders'],
                "avg_price": round(r['avg_price'], 2),
                "avg_freight": round(r['avg_freight'], 2),
                "avg_installments": round(r['avg_installments'], 2),
            } for r in panel
        ],
    }


if __name__ == "__main__":
    if not os.environ.get("KAGGLE_API_TOKEN"):
        print("⚠️  Set KAGGLE_API_TOKEN env var to run.")
        exit(0)

    print("\n── Top 10 categories ──")
    cats = list_categories(min_orders=500)
    for c in cats[:10]:
        print(f"  {c['pt']:35s} ({c['en']:30s}) {c['n_orders']:>6,}")

    print("\n── query_sales_data('esporte_lazer') ──")
    r = query_sales_data('esporte_lazer')
    for k, v in r.items():
        if k == 'monthly_panel':
            print(f"  {k}: {len(v)} months")
            print(f"    first: {v[0] if v else None}")
            print(f"    last:  {v[-1] if v else None}")
        else:
            print(f"  {k}: {v}")

    print("\n── query_sales_data('xyz_does_not_exist') ──")
    print(query_sales_data('xyz_does_not_exist'))
