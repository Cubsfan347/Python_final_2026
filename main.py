import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st


MENU_PATH = Path(__file__).with_name("menu.txt")
ORDERS_PATH = Path(__file__).with_name("orders.jsonl")
PICKUP_ADDRESS = "Placeholder — awaiting LAC Burgers' verified Chicago address."
RESTAURANT_HOURS = "Placeholder — awaiting confirmed weekly hours."
PICKUP_ESTIMATE_MINUTES = 20
TOPPING_PRICE_CENTS = 25
DELIVERY_FEE_CENTS_PER_ITEM = 300
PICKUP = "Pickup"
DELIVERY = "Delivery"
PAY_AT_PICKUP = "Pay at pickup"
PAY_ON_DELIVERY = "Pay on delivery"
MENU_CATEGORIES = (
    "SIZES",
    "CHEESES",
    "CONDIMENTS",
    "TOPPINGS",
    "DRINKS",
    "DRINK_SIZE",
)
BURGER_PRICES = {"single": 2, "double": 4, "triple": 8}
DRINK_PRICES = {"small": 1, "medium": 2, "large": 3}
TEST_PAYMENT = "Test online payment (no charge)"
ORDER_FIELDS = (
    "order_id",
    "ordered_at",
    "pickup_at",
    "name",
    "phone",
    "total",
)
LEGACY_ORDER_FIELDS = (
    "size",
    "cheese",
    "condiments",
    "toppings",
    "drink",
    "drink_size",
)
ITEM_FIELDS = (
    "size",
    "cheese",
    "condiments",
    "toppings",
    "drink",
    "drink_size",
)


def load_menu() -> dict[str, list[str]]:
    menu: dict[str, list[str]] = {}
    with MENU_PATH.open("r", encoding="utf-8") as menu_file:
        for line_number, line in enumerate(menu_file, start=1):
            if not line.strip():
                continue
            category, separator, choices = line.partition(":")
            if not separator:
                raise ValueError(f"Menu line {line_number} is missing a colon.")
            menu[category.strip()] = [
                choice.strip() for choice in choices.split(",") if choice.strip()
            ]

    missing_categories = [category for category in MENU_CATEGORIES if not menu.get(category)]
    if missing_categories:
        raise ValueError(
            "The menu is missing categories: " + ", ".join(missing_categories)
        )
    return menu


def normalize_phone(phone: str) -> str:
    return "".join(character for character in phone if character.isdigit())


def read_orders(phone: str | None = None) -> tuple[list[dict], list[str]]:
    orders = []
    errors = []
    try:
        with ORDERS_PATH.open("r", encoding="utf-8") as order_file:
            for line_number, line in enumerate(order_file, start=1):
                if not line.strip():
                    continue
                try:
                    order = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"Could not read saved order on line {line_number}.")
                    continue
                if not isinstance(order, dict) or not all(
                    field in order for field in ORDER_FIELDS
                ):
                    errors.append(f"Saved order on line {line_number} has invalid data.")
                    continue
                if "items" in order:
                    items = order["items"]
                    if not isinstance(items, list) or not items or any(
                        not isinstance(item, dict)
                        or not all(field in item for field in ITEM_FIELDS)
                        for item in items
                    ):
                        errors.append(
                            f"Saved order on line {line_number} has invalid data."
                        )
                        continue
                elif not all(field in order for field in LEGACY_ORDER_FIELDS):
                    errors.append(f"Saved order on line {line_number} has invalid data.")
                    continue
                if phone is None or order["phone"] == phone:
                    orders.append(order)
    except FileNotFoundError:
        return orders, errors
    return orders, errors


def save_order(order: dict) -> None:
    with ORDERS_PATH.open("a", encoding="utf-8") as order_file:
        order_file.write(json.dumps(order, ensure_ascii=False) + "\n")


def money_cents(amount: int) -> str:
    return f"${amount // 100}.{amount % 100:02d}"


def order_total_cents(order: dict) -> int:
    if "total_cents" in order:
        return int(order["total_cents"])
    return round(float(order["total"]) * 100)


def item_total_cents(item: dict) -> int:
    burger_cents = BURGER_PRICES[item["size"].lower()] * 100
    drink_cents = DRINK_PRICES[item["drink_size"].lower()] * 100
    topping_cents = len(item["toppings"]) * TOPPING_PRICE_CENTS
    return burger_cents + drink_cents + topping_cents


def delivery_total_cents(order: dict) -> int:
    if order.get("fulfillment_method") == DELIVERY:
        return len(order_items(order)) * DELIVERY_FEE_CENTS_PER_ITEM
    return 0


def order_items(order: dict) -> list[dict]:
    if "items" in order:
        return order["items"]
    return [{field: order[field] for field in ITEM_FIELDS}]


def order_summary(order: dict) -> None:
    for index, item in enumerate(order_items(order), start=1):
        st.write(
            f"**Burger {index}: {item['size'].title()}** with {item['cheese']} "
            f"· {money_cents(item_total_cents(item))}"
        )
        st.write(f"**Drink:** {item['drink'].title()} ({item['drink_size']})")
        st.write(f"**Condiments:** {', '.join(item['condiments']) or 'None'}")
        st.write(f"**Toppings:** {', '.join(item['toppings']) or 'None'}")
        if item["toppings"]:
            st.caption(
                f"Topping charge: {len(item['toppings'])} × "
                f"{money_cents(TOPPING_PRICE_CENTS)}"
            )
    st.write("Condiments are included. Each selected topping costs $0.25.")


def add_item_to_cart(menu: dict[str, list[str]]) -> None:
    item = {
        "size": st.session_state["size"],
        "cheese": st.session_state["cheese"],
        "condiments": [
            choice
            for index, choice in enumerate(menu["CONDIMENTS"])
            if st.session_state.get(f"condiments_{index}", False)
        ],
        "toppings": [
            choice
            for index, choice in enumerate(menu["TOPPINGS"])
            if st.session_state.get(f"toppings_{index}", False)
        ],
        "drink": st.session_state["drink"],
        "drink_size": st.session_state["drink_size"],
    }
    st.session_state.setdefault("cart", []).append(item)
    for category in ("condiments", "toppings"):
        for index in range(len(menu[category.upper()])):
            st.session_state[f"{category}_{index}"] = False


def render_order_form(menu: dict[str, list[str]]) -> None:
    st.subheader("Your details")
    name = st.text_input("Name", key="name", max_chars=80)
    phone = st.text_input(
        "Phone number",
        key="phone",
        help="Used to look up your recent orders.",
        max_chars=24,
    )
    fulfillment_method = st.radio(
        "How would you like your order?",
        [PICKUP, DELIVERY],
        key="fulfillment_method",
        horizontal=True,
    )
    delivery_address = ""
    if fulfillment_method == DELIVERY:
        delivery_address = st.text_area(
            "Delivery address",
            key="delivery_address",
            max_chars=300,
            help="Enter the complete Chicago delivery address, including apartment or unit if needed.",
        )
        st.caption(
            "Delivery coverage and timing are not yet verified by the app. "
            "Confirm that your address is serviceable with LAC Burgers."
        )

    st.subheader("Build a burger")
    size = st.selectbox("Burger size", menu["SIZES"], key="size")
    cheese = st.selectbox("Cheese", menu["CHEESES"], key="cheese")

    left_column, right_column = st.columns(2)
    with left_column:
        st.markdown("**Condiments**")
        condiments = [
            choice
            for index, choice in enumerate(menu["CONDIMENTS"])
            if st.checkbox(choice.title(), key=f"condiments_{index}")
        ]

    with right_column:
        st.markdown("**Toppings**")
        toppings = [
            choice
            for index, choice in enumerate(menu["TOPPINGS"])
            if st.checkbox(choice.title(), key=f"toppings_{index}")
        ]

    st.subheader("Choose a drink")
    drink_column, drink_size_column = st.columns(2)
    with drink_column:
        drink = st.selectbox("Drink", menu["DRINKS"], key="drink")
    with drink_size_column:
        drink_size = st.selectbox("Drink size", menu["DRINK_SIZE"], key="drink_size")

    current_item = {
        "size": size,
        "cheese": cheese,
        "condiments": condiments,
        "toppings": toppings,
        "drink": drink,
        "drink_size": drink_size,
    }
    current_total = item_total_cents(current_item)
    st.markdown(
        f"**This burger and drink: {money_cents(current_total)}** "
        f"(includes {money_cents(len(toppings) * TOPPING_PRICE_CENTS)} "
        "for toppings)"
    )
    st.button("Add burger to cart", on_click=add_item_to_cart, args=(menu,))

    cart = st.session_state.setdefault("cart", [])
    st.subheader(f"Your cart ({len(cart)} {'item' if len(cart) == 1 else 'items'})")
    if not cart:
        st.caption("Add a burger and drink to get started.")
        return

    st.caption("To change a meal, remove it and add it again.")
    for index, item in enumerate(cart):
        st.write(
            f"**{index + 1}. {item['size'].title()} burger + "
            f"{item['drink_size'].title()} {item['drink'].title()}** "
            f"— {money_cents(item_total_cents(item))}"
        )
        st.caption(
            f"{item['cheese'].title()} cheese · "
            f"Condiments: {', '.join(item['condiments']) or 'None'} · "
            f"Toppings: {', '.join(item['toppings']) or 'None'}"
        )
        if st.button("Remove", key=f"remove_cart_item_{index}"):
            cart.pop(index)
            st.rerun()

    cart_items_total = sum(item_total_cents(item) for item in cart)
    delivery_fee = (
        len(cart) * DELIVERY_FEE_CENTS_PER_ITEM
        if fulfillment_method == DELIVERY
        else 0
    )
    if delivery_fee:
        st.write(
            f"Delivery fee: {len(cart)} × "
            f"{money_cents(DELIVERY_FEE_CENTS_PER_ITEM)} = "
            f"{money_cents(delivery_fee)}"
        )
    cart_total = cart_items_total + delivery_fee
    st.markdown(f"### Current total: {money_cents(cart_total)}")
    if st.button("Review order", type="primary"):
        customer_name = name.strip()
        customer_phone = normalize_phone(phone)
        if not customer_name:
            st.error("Enter your name to continue.")
        elif not 7 <= len(customer_phone) <= 15:
            st.error("Enter a valid phone number with 7 to 15 digits.")
        elif fulfillment_method == DELIVERY and not delivery_address.strip():
            st.error("Enter a delivery address to continue.")
        else:
            st.session_state.draft_order = {
                "name": customer_name,
                "phone": customer_phone,
                "items": [dict(item) for item in cart],
                "total": cart_total / 100,
                "total_cents": cart_total,
                "fulfillment_method": fulfillment_method,
                "delivery_address": (
                    delivery_address.strip()
                    if fulfillment_method == DELIVERY
                    else ""
                ),
            }
            st.session_state.order_stage = "review"
            st.rerun()


def render_review() -> None:
    order = st.session_state.draft_order
    st.subheader("Review your order")
    st.caption(f"Customer: {order['name']} · Phone: {order['phone']}")
    order_summary(order)

    st.subheader("Price breakdown")
    for index, item in enumerate(order_items(order), start=1):
        st.write(
            f"Burger {index} and {item['drink_size']} drink"
            f" ({len(item['toppings'])} topping"
            f"{'' if len(item['toppings']) == 1 else 's'}): "
            f"{money_cents(item_total_cents(item))}"
        )
    delivery_fee = delivery_total_cents(order)
    if delivery_fee:
        st.write(
            f"Delivery fee ({len(order_items(order))} × "
            f"{money_cents(DELIVERY_FEE_CENTS_PER_ITEM)}): "
            f"{money_cents(delivery_fee)}"
        )
    st.markdown(f"### Total: {money_cents(order_total_cents(order))}")
    st.write(f"**Fulfillment:** {order.get('fulfillment_method', PICKUP)}")
    if order.get("fulfillment_method") == DELIVERY:
        st.write(f"**Delivery address:** {order['delivery_address']}")
    in_person_payment = (
        PAY_ON_DELIVERY
        if order.get("fulfillment_method") == DELIVERY
        else PAY_AT_PICKUP
    )
    payment_choice = st.radio(
        "Payment option",
        [in_person_payment, TEST_PAYMENT],
        key="payment_choice",
        help="Test payment only simulates success. It does not collect card details or charge money.",
    )
    if payment_choice == TEST_PAYMENT:
        st.warning(
            "Test mode only: choosing this option will mark the order as "
            "simulated paid. No payment is processed and no charge is made."
        )
    else:
        st.info(f"Payment is due in person ({in_person_payment.lower()}).")
    if order.get("fulfillment_method") != DELIVERY:
        st.caption(
            f"Estimated pickup is about {PICKUP_ESTIMATE_MINUTES} minutes after "
            "confirmation. Actual timing may vary."
        )
    else:
        st.caption("Delivery timing is not available in the app; please confirm it with the restaurant.")

    edit_column, confirm_column = st.columns(2)
    with edit_column:
        if st.button("Back to cart"):
            st.session_state.order_stage = "build"
            st.rerun()
    with confirm_column:
        button_label = (
            "Simulate test payment and place order"
            if payment_choice == TEST_PAYMENT
            else "Confirm and place order"
        )
        if st.button(button_label, type="primary"):
            ordered_at = datetime.now().astimezone()
            confirmed_order = {
                **order,
                "total": order_total_cents(order) / 100,
                "total_cents": order_total_cents(order),
                "payment_method": (
                    "test_online"
                    if payment_choice == TEST_PAYMENT
                    else (
                        "pay_on_delivery"
                        if order.get("fulfillment_method") == DELIVERY
                        else "pay_at_pickup"
                    )
                ),
                "payment_status": (
                    "simulated_paid"
                    if payment_choice == TEST_PAYMENT
                    else (
                        "due_at_delivery"
                        if order.get("fulfillment_method") == DELIVERY
                        else "due_at_pickup"
                    )
                ),
                "order_id": uuid.uuid4().hex[:8].upper(),
                "ordered_at": ordered_at.isoformat(),
                "pickup_at": (
                    (
                        ordered_at + timedelta(minutes=PICKUP_ESTIMATE_MINUTES)
                    ).isoformat()
                    if order.get("fulfillment_method") != DELIVERY
                    else ""
                ),
            }
            try:
                save_order(confirmed_order)
            except OSError as error:
                st.error(f"Could not save your order: {error}")
            else:
                st.session_state.confirmed_order = confirmed_order
                st.session_state.order_stage = "confirmed"
                st.rerun()


def render_confirmation() -> None:
    order = st.session_state.confirmed_order
    st.success("Your order is confirmed.")
    st.markdown(f"### Order {order['order_id']}")
    order_summary(order)
    st.markdown(f"### Total: {money_cents(order_total_cents(order))}")
    if order.get("payment_status") == "simulated_paid":
        st.success("Test payment successful. No charge was made.")
    elif order.get("fulfillment_method") == DELIVERY:
        st.info("Payment is due on delivery.")
    else:
        st.info("Payment is due at pickup.")
    if order.get("fulfillment_method") == DELIVERY:
        st.write(f"**Delivery address:** {order['delivery_address']}")
        st.caption("Please confirm delivery timing and coverage with the restaurant.")
    elif order.get("pickup_at"):
        st.write(
            "**Estimated pickup (may vary):** "
            + datetime.fromisoformat(order["pickup_at"]).strftime("%I:%M %p %Z")
        )
    if order.get("fulfillment_method") == DELIVERY:
        st.info("Delivery coverage and timing are not verified; confirm them with LAC Burgers.")
    else:
        st.info(
            "Please confirm the pickup location and current hours with LAC Burgers "
            "before traveling; those details are placeholders."
        )

    if st.button("Start another order"):
        for key in (
            "name",
            "phone",
            "size",
            "cheese",
            "drink",
            "drink_size",
            "delivery_address",
        ):
            st.session_state.pop(key, None)
        for key in list(st.session_state):
            if key.startswith(("condiments_", "toppings_")):
                st.session_state.pop(key, None)
        st.session_state.order_stage = "build"
        st.session_state.cart = []
        st.session_state.pop("payment_choice", None)
        st.session_state.pop("fulfillment_method", None)
        st.session_state.pop("draft_order", None)
        st.session_state.pop("confirmed_order", None)
        st.rerun()


def render_recent_orders() -> None:
    with st.form("order_lookup_form"):
        phone_input = st.text_input(
            "Phone number", key="lookup_phone_input", max_chars=24
        )
        lookup_submitted = st.form_submit_button("Find recent orders")

    if lookup_submitted:
        lookup_phone = normalize_phone(phone_input)
        if not 7 <= len(lookup_phone) <= 15:
            st.error("Enter a valid phone number with 7 to 15 digits.")
            st.session_state.pop("lookup_phone", None)
        else:
            st.session_state.lookup_phone = lookup_phone

    lookup_phone = st.session_state.get("lookup_phone")
    if not lookup_phone:
        st.caption("Enter the phone number used for your orders to look them up.")
        return

    try:
        orders, errors = read_orders(lookup_phone)
    except OSError as error:
        st.error(f"Could not read saved order history: {error}")
        return

    for error in errors:
        st.warning(error)
    recent_orders = sorted(
        orders, key=lambda order: order["ordered_at"], reverse=True
    )[:5]
    if not recent_orders:
        st.info("No saved orders were found for that phone number.")
        return

    for order in recent_orders:
        with st.container(border=True):
            st.markdown(
                f"**Order {order['order_id']} · "
                f"{money_cents(order_total_cents(order))}**"
            )
            st.caption(
                f"Fulfillment: {order.get('fulfillment_method', PICKUP)}"
            )
            if order.get("payment_status") == "simulated_paid":
                st.caption("Test payment (simulated; no charge)")
            elif order.get("payment_status") == "due_at_delivery":
                st.caption("Payment due on delivery")
            elif order.get("payment_status") == "due_at_pickup":
                st.caption("Payment due at pickup")
            st.caption(
                datetime.fromisoformat(order["ordered_at"]).strftime(
                    "%b %d, %Y at %I:%M %p %Z"
                )
            )
            order_summary(order)


def main() -> None:
    st.set_page_config(page_title="LAC Burgers", page_icon="🍔", layout="centered")
    st.markdown(
        """
        <style>
        .stApp { background: #fffaf3; }
        [data-testid="stHeader"] { background: rgba(255, 250, 243, 0.9); }
        h1, h2, h3 { color: #53291d; }
        div.stButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primary"] {
            background: #a63d22;
            border-color: #a63d22;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("LAC Burgers")
    st.write("Build your burgers, choose pickup or delivery, and review your order.")
    st.info(
        f"**Restaurant / pickup address:** {PICKUP_ADDRESS}\n\n"
        f"**Restaurant hours:** {RESTAURANT_HOURS}\n\n"
        f"Pickup estimate: about {PICKUP_ESTIMATE_MINUTES} minutes after "
        "confirmation; actual timing may vary. This estimate does not check "
        "opening hours or live kitchen capacity, and no pickup time is reserved. "
        "Delivery service coverage and timing are not yet verified."
    )
    st.sidebar.info(
        "Demo storage: order history is kept in a local text file and may be "
        "lost when the app is redeployed on Streamlit Community Cloud."
    )

    try:
        menu = load_menu()
    except FileNotFoundError:
        st.error(f"Menu file not found: {MENU_PATH.name}")
        st.stop()
    except ValueError as error:
        st.error(f"Could not load the menu: {error}")
        st.stop()

    if any(size.lower() not in BURGER_PRICES for size in menu["SIZES"]):
        st.error("The menu burger sizes must be single, double, and triple.")
        st.stop()
    if any(size.lower() not in DRINK_PRICES for size in menu["DRINK_SIZE"]):
        st.error("The menu drink sizes must be small, medium, and large.")
        st.stop()

    if "order_stage" not in st.session_state:
        st.session_state.order_stage = "build"

    order_tab, history_tab = st.tabs(["Place an order", "Recent orders"])
    with order_tab:
        stage = st.session_state.order_stage
        if stage == "build":
            render_order_form(menu)
        elif stage == "review":
            render_review()
        elif stage == "confirmed":
            render_confirmation()

    with history_tab:
        render_recent_orders()


if __name__ == "__main__":
    main()
