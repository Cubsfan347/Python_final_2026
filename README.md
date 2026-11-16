# Burger Order

A Streamlit burger-ordering demo with editable order review, menu-based pricing,
pay-at-pickup confirmation, and recent-order lookup.

## Run locally

From this directory, install the dependency and start the app:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run streamlit_app.py
```

The menu is read from `menu.txt`. Burger prices are $2 for single, $4 for
double, and $8 for triple. Drinks are $1 small, $2 medium, and $3 large.
Condiments and toppings are included in the burger price.

## Deploy on Streamlit Community Cloud

Create a Community Cloud app from this GitHub repository, select the `main`
branch, and set `streamlit_app.py` as the app's entry point. Community Cloud installs
the dependency from `requirements.txt`.

Confirmed orders are appended as JSON Lines to `orders.jsonl`; the existing
`orders.txt` and `customer_list.txt` files are left untouched because they
contain legacy command-line data. This file-based storage is intended for a
demo. Streamlit Community Cloud does not guarantee local files will persist
across redeployments, and the app does not process online payments. Use a
persistent database before using the app for real customer orders.
