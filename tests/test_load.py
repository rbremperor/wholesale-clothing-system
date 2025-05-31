import requests
import random
import threading
import time

BASE_URL = "http://localhost:8000"  # Change for production
CONCURRENT_USERS = 50
REQUESTS_PER_USER = 20


def create_product():
    product_data = {
        "name": f"Product-{random.randint(1000, 9999)}",
        "category": random.choice(["Tops", "Bottoms", "Outerwear"]),
        "size": random.choice(["S", "M", "L", "XL"]),
        "quantity": random.randint(10, 100),
        "price": round(random.uniform(10, 100), 2)
    }
    response = requests.post(f"{BASE_URL}/add_product", data=product_data)
    return response.status_code == 200


def place_order():
    # Get available products
    inventory = requests.get(f"{BASE_URL}/api/inventory").json()
    if not inventory["inventory"]:
        return False

    product = random.choice(inventory["inventory"])
    order_data = {
        "product_id": product[0],
        "customer_name": f"Customer-{random.randint(1000, 9999)}",
        "quantity": random.randint(1, 5),
        "order_date": "2023-06-20"
    }
    response = requests.post(f"{BASE_URL}/place_order", data=order_data)
    return response.status_code == 200


def simulate_user(user_id):
    successes = 0
    for _ in range(REQUESTS_PER_USER):
        if random.random() > 0.7:  # 30% chance to create product
            success = create_product()
        else:  # 70% chance to place order
            success = place_order()

        if success:
            successes += 1

    print(f"User {user_id} completed {successes}/{REQUESTS_PER_USER} successful actions")


def run_load_test():
    start_time = time.time()
    threads = []

    print(f"Starting load test with {CONCURRENT_USERS} users...")

    for i in range(CONCURRENT_USERS):
        t = threading.Thread(target=simulate_user, args=(i + 1,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    duration = time.time() - start_time
    total_requests = CONCURRENT_USERS * REQUESTS_PER_USER
    rps = total_requests / duration

    print(f"\nLoad test completed in {duration:.2f} seconds")
    print(f"Total requests: {total_requests}")
    print(f"Requests per second: {rps:.2f}")


if __name__ == "__main__":
    run_load_test()