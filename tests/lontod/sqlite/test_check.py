"""tests the check module."""

from sqlite3 import connect

import pytest

from lontod.sqlite.check import DatabaseDiff, diff_database, is_open, make_test_database

_sample_one: str = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    age INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert some dummy data into the 'users' table
INSERT INTO users (name, email, age) VALUES
('Alice Smith', 'alice@example.com', 30),
('Bob Johnson', 'bob@example.com', 25),
('Charlie Brown', 'charlie@example.com', 35),
('Diana Prince', 'diana@example.com', 28),
('Ethan Hunt', 'ethan@example.com', 40);
"""

_sample_one_half: str = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    age INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert some dummy data into the 'users' table
INSERT INTO users (name, email, age) VALUES
('Alice Smith', 'alice@example.com', 30),
('Bob Johnson', 'bob@example.com', 25),
('Charlie Brown', 'charlie@example.com', 35);
"""

_sample_two: str = """
-- Create a table named 'products'
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock_quantity INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert some dummy data into the 'products' table
INSERT INTO products (product_name, category, price, stock_quantity) VALUES
('Laptop', 'Electronics', 999.99, 50),
('Smartphone', 'Electronics', 499.99, 150),
('Coffee Maker', 'Home Appliances', 79.99, 75),
('Desk Chair', 'Furniture', 149.99, 30),
('Wireless Mouse', 'Electronics', 29.99, 200);
"""


EMPTY_DIFF: DatabaseDiff = {
    "left": set(),
    "right": set(),
    "diff": [],
}


@pytest.mark.parametrize(
    ("left_src", "right_src", "want_equal"),
    [
        (_sample_one, _sample_one, True),
        (_sample_one, _sample_one_half, False),
        (_sample_one, _sample_two, False),
        (_sample_two, _sample_one, False),
        (_sample_two, _sample_two, True),
    ],
)
def test_assert_table_equals(left_src: str, right_src: str, want_equal: bool) -> None:
    """Tests that two tables are identical."""
    try:
        left = make_test_database(left_src)
        right = make_test_database(right_src)

        got = diff_database(left, right)
        if want_equal:
            assert got == EMPTY_DIFF
        else:
            assert got != EMPTY_DIFF
    finally:
        left.close()
        right.close()


def test_is_open() -> None:
    """Tests the is_open function."""
    conn = connect("file:?mode=memory")
    try:
        assert is_open(conn)
    finally:
        conn.close()

    assert not is_open(conn)
