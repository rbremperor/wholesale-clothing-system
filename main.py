from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
import uvicorn
from datetime import datetime

app = FastAPI(title="Wholesale Clothing Cloud System")

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Database initialization
def init_db():
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()

    # Create products table
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

    # Create orders table
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


# Helper function to get counts for home page
def get_counts():
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM products")
    products_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders")
    orders_count = c.fetchone()[0]

    conn.close()
    return products_count, orders_count


# Application routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    products_count, orders_count = get_counts()
    return templates.TemplateResponse("home.html", {
        "request": request,
        "products_count": products_count,
        "orders_count": orders_count
    })


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()

    c.execute("SELECT * FROM products")
    products = c.fetchall()

    c.execute("""
              SELECT o.id, p.name, o.customer_name, o.quantity, o.order_date
              FROM orders o
                       JOIN products p ON o.product_id = p.id
              ORDER BY o.order_date DESC LIMIT 10
              """)
    orders = c.fetchall()

    conn.close()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "products": products,
        "orders": orders
    })


@app.get("/inventory", response_class=HTMLResponse)
async def inventory_management(request: Request):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()
    c.execute("SELECT * FROM products ORDER BY name")
    products = c.fetchall()
    conn.close()
    return templates.TemplateResponse("inventory.html", {
        "request": request,
        "products": products
    })


@app.get("/orders", response_class=HTMLResponse)
async def orders_management(request: Request):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()
    c.execute("""
              SELECT o.id, p.name, o.customer_name, o.quantity, o.order_date
              FROM orders o
                       JOIN products p ON o.product_id = p.id
              ORDER BY o.order_date DESC
              """)
    orders = c.fetchall()
    conn.close()
    return templates.TemplateResponse("orders.html", {
        "request": request,
        "orders": orders
    })


@app.get("/products/add", response_class=HTMLResponse)
async def add_product_form(request: Request):
    return templates.TemplateResponse("add_product.html", {"request": request})


@app.get("/orders/add", response_class=HTMLResponse)
async def add_order_form(request: Request):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()
    c.execute("SELECT id, name FROM products ORDER BY name")
    products = c.fetchall()
    conn.close()
    return templates.TemplateResponse("add_order.html", {
        "request": request,
        "products": products,
        "today": datetime.now().strftime("%Y-%m-%d")
    })


@app.post("/add_product")
async def add_product(
        request: Request,
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
    return RedirectResponse(url="/inventory", status_code=303)


@app.post("/place_order")
async def place_order(
        request: Request,
        product_id: int = Form(...),
        customer_name: str = Form(...),
        quantity: int = Form(...),
        order_date: str = Form(...)
):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()

    # Check product availability
    c.execute("SELECT quantity, name FROM products WHERE id = ?", (product_id,))
    result = c.fetchone()

    if not result or result[0] < quantity:
        c.execute("SELECT id, name FROM products ORDER BY name")
        products = c.fetchall()
        conn.close()
        return templates.TemplateResponse("add_order.html", {
            "request": request,
            "error": "Insufficient stock or invalid product",
            "products": products,
            "today": datetime.now().strftime("%Y-%m-%d"),
            "preserve_input": {
                "product_id": product_id,
                "customer_name": customer_name,
                "quantity": quantity,
                "order_date": order_date
            }
        })

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
    return RedirectResponse(url="/orders", status_code=303)


# API endpoints
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
    c.execute("""
              SELECT o.id, p.name, o.customer_name, o.quantity, o.order_date
              FROM orders o
                       JOIN products p ON o.product_id = p.id
              """)
    orders = c.fetchall()
    conn.close()
    return {"orders": orders}


# Add these new routes to main.py

@app.get("/products/edit/{product_id}", response_class=HTMLResponse)
async def edit_product_form(request: Request, product_id: int):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()

    if not product:
        return RedirectResponse(url="/inventory", status_code=303)

    return templates.TemplateResponse("edit_product.html", {
        "request": request,
        "product": product
    })


@app.post("/products/update/{product_id}")
async def update_product(
        request: Request,
        product_id: int,
        name: str = Form(...),
        category: str = Form(...),
        size: str = Form(...),
        quantity: int = Form(...),
        price: float = Form(...)
):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()

    # Update product
    c.execute("""
              UPDATE products
              SET name     = ?,
                  category = ?,
                  size     = ?,
                  quantity = ?,
                  price    = ?
              WHERE id = ?
              """, (name, category, size, quantity, price, product_id))

    conn.commit()
    conn.close()
    return RedirectResponse(url="/inventory", status_code=303)


@app.get("/products/delete/{product_id}")
async def delete_product(request: Request, product_id: int):
    conn = sqlite3.connect("clothing.db")
    c = conn.cursor()

    # First check if there are any orders for this product
    c.execute("SELECT 1 FROM orders WHERE product_id = ? LIMIT 1", (product_id,))
    has_orders = c.fetchone()

    if has_orders:
        conn.close()
        return templates.TemplateResponse("inventory.html", {
            "request": request,
            "products": c.execute("SELECT * FROM products").fetchall(),
            "error": "Cannot delete product with existing orders"
        })

    # Delete product
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/inventory", status_code=303)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)