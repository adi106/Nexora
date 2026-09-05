from sqlalchemy import text

from backend.app.db.session import engine


def verify_catalog():
    query = text(
        """
        SELECT
            u.email,
            s.store_name,
            c.name AS category,
            p.name AS product,
            pv.sku,
            pv.price,
            i.quantity,
            i.reserved_quantity,
            i.quantity - i.reserved_quantity AS available_stock
        FROM users u
        JOIN sellers s
            ON s.user_id = u.id
        JOIN products p
            ON p.seller_id = s.id
        JOIN categories c
            ON c.id = p.category_id
        JOIN product_variants pv
            ON pv.product_id = p.id
        JOIN inventory i
            ON i.variant_id = pv.id;
        """
    )

    with engine.connect() as connection:
        result = connection.execute(query)

        for row in result:
            print(dict(row._mapping))


if __name__ == "__main__":
    verify_catalog()