# LAC Burgers

A Streamlit burger-ordering demo with live item pricing, a multi-burger cart,
editable order review, pay-at-pickup or simulated test-payment confirmation,
and recent-order lookup.

## Run locally

From this directory, install the dependency and start the app:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run streamlit_app.py
```

The menu is read from `menu.txt`. Burger prices are $2 for single, $4 for
double, and $8 for triple. Drinks are $1 small, $2 medium, and $3 large.
Condiments are included. Each selected topping costs $0.25 per burger. Customers
can choose pickup or delivery; delivery adds $3.00 per burger-and-drink item.
The cart and review totals include these charges and update as items are added
or removed. The app currently does not calculate tax or other fees.

Delivery requires a complete address, but the app does not validate delivery
coverage or provide an estimated delivery time. Confirm service area and timing
with LAC Burgers before relying on delivery orders.

The pickup address and weekly hours in the app are clearly marked placeholders
because verified LAC Burgers details have not yet been provided. Replace
`PICKUP_ADDRESS` and `RESTAURANT_HOURS` in `main.py` with confirmed information
before publishing. Pickup is estimated at about 20 minutes after order
confirmation; this is not a live kitchen availability estimate, so customers
are told that timing may vary.

## Payment options

The app supports pay-at-pickup and a **test-only simulated payment** option.
The test option does not collect card details, connect to a payment provider,
or charge money; it only records a simulated-paid status on the order. It is
for exercising the UI and is not suitable for accepting real online payments.
Real payments require integration with a payment provider and verified
server-side payment confirmation.

## Deploy on Streamlit Community Cloud

Create a Community Cloud app from this GitHub repository, select the `main`
branch, and set `streamlit_app.py` as the app's entry point. Community Cloud installs
the dependency from `requirements.txt`.

Confirmed orders are appended as JSON Lines to `orders.jsonl`; the existing
`orders.txt` and `customer_list.txt` files are left untouched because they
contain legacy command-line data. This file-based storage is intended for a
demo. Streamlit Community Cloud does not guarantee local files will persist
across redeployments. Use a persistent database and a real payment-provider
integration before using the app for real customer orders or payments.
