# db/init_sqlite.py
import sqlite3, os
os.makedirs("db", exist_ok=True)
con = sqlite3.connect("db/retail.db")
cur = con.cursor()

cur.executescript("""
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE customers(
  customer_id INTEGER PRIMARY KEY,
  segment TEXT,
  region TEXT
);

CREATE TABLE products(
  product_id INTEGER PRIMARY KEY,
  category TEXT,
  price REAL
);

CREATE TABLE sales(
  sale_id INTEGER PRIMARY KEY,
  customer_id INTEGER,
  product_id INTEGER,
  sale_date TEXT,
  qty INTEGER,
  revenue REAL,
  FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
  FOREIGN KEY(product_id) REFERENCES products(product_id)
);
""")

cur.executemany("INSERT INTO customers VALUES(?,?,?)", [
  (1,"Enterprise","NA"), (2,"SMB","EU"), (3,"Enterprise","APAC"), (4,"SMB","NA")
])

cur.executemany("INSERT INTO products VALUES(?,?,?)", [
  (10,"Hardware",799.0), (11,"Software",199.0), (12,"Services",499.0)
])

cur.executemany("INSERT INTO sales VALUES(?,?,?,?,?,?)", [
  (100,1,10,"2024-04-12",1,799.0),
  (101,2,11,"2024-05-03",3,597.0),
  (102,3,12,"2024-05-21",2,998.0),
  (103,1,11,"2024-06-10",5,995.0),
  (104,4,10,"2024-06-22",1,799.0),
])

con.commit()
con.close()
print("✅ SQLite db/retail.db ready.")
