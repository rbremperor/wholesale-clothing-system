from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
import os
import uvicorn

app = FastAPI(title="Wholesale Clothing Cloud System")

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Database initialization
def init_db():
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()

    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     name
                     TEXT
                     NOT
                     NULL,
                     category
                     TEXT,
                     size
                     TEXT,
                     quantity
                     INTEGER,
                     price
                     REAL
                 )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        product_id
        INTEGER,
        customer_name
        TEXT,
        quantity
        INTEGER,
        order_date
        TEXT,
        FOREIGN
        KEY
                 (
        product_id
                 ) REFERENCES products
                 (
                     id
                 ))''')

    # Insert sample data if empty
    if not c.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        sample_products = [
            ("Men's T-Shirt", "Tops", "M", 100, 12.99),
            ("Women's Jeans", "Bottoms", "L", 75, 29.99),
            ("Unisex Hoodie", "Outerwear", "XL", 50, 39.99)
        ]
        c.executemany("INSERT INTO products (name, category, size, quantity, price) VALUES (?, ?, ?, ?, ?)",
                      sample_products)

    conn.commit()
    conn.close()


init_db()


# Data models
class Product(BaseModel):
    name: str
    category: str
    size: str
    quantity: int
    price: float


class Order(BaseModel):
    product_id: int
    customer_name: str
    quantity: int
    order_date: str


# Application routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()

    c.execute("SELECT * FROM products")
    products = c.fetchall()

    c.execute(
        "SELECT o.id, p.name, o.customer_name, o.quantity, o.order_date FROM orders o JOIN products p ON o.product_id = p.id")
    orders = c.fetchall()

    conn.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products,
        "orders": orders
    })


@app.post("/add_product")
async def add_product(
        name: str = Form(...),
        category: str = Form(...),
        size: str = Form(...),
        quantity: int = Form(...),
        price: float = Form(...)
):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO products (name, category, size, quantity, price) VALUES (?, ?, ?, ?, ?)",
        (name, category, size, quantity, price)
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Product added successfully"}


@app.post("/place_order")
async def place_order(
        product_id: int = Form(...),
        customer_name: str = Form(...),
        quantity: int = Form(...),
        order_date: str = Form(...)
):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()

    # Check product availability
    c.execute("SELECT quantity FROM products WHERE id = ?", (product_id,))
    result = c.fetchone()

    if not result or result[0] < quantity:
        conn.close()
        return {"status": "error", "message": "Insufficient stock or invalid product"}

    # Place order
    c.execute(
        "INSERT INTO orders (product_id, customer_name, quantity, order_date) VALUES (?, ?, ?, ?)",
        (product_id, customer_name, quantity, order_date)
    )

    # Update inventory
    c.execute(
        "UPDATE products SET quantity = quantity - ? WHERE id = ?",
        (quantity, product_id)
    )

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Order placed successfully"}


@app.get("/api/inventory")
async def get_inventory():
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return {"inventory": products}


@app.get("/api/orders")
async def get_orders():
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()
    c.execute(
        "SELECT o.id, p.name, o.customer_name, o.quantity, o.order_date FROM orders o JOIN products p ON o.product_id = p.id")
    orders = c.fetchall()
    conn.close()
    return {"orders": orders}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)