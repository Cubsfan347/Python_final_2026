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


def money(amount: int) -> str:
    return f"${amount:.2f}"


def item_total(item: dict) -> int:
    return BURGER_PRICES[item["size"].lower()] + DRINK_PRICES[
        item["drink_size"].lower()
    ]


def order_items(order: dict) -> list[dict]:
    if "items" in order:
        return order["items"]
    return [{field: order[field] for field in ITEM_FIELDS}]


def order_summary(order: dict) -> None:
    for index, item in enumerate(order_items(order), start=1):
        st.write(
            f"**Burger {index}: {item['size'].title()}** with {item['cheese']} "
            f"· {money(item_total(item))}"
        )
        st.write(f"**Drink:** {item['drink'].title()} ({item['drink_size']})")
        st.write(f"**Condiments:** {', '.join(item['condiments']) or 'None'}")
        st.write(f"**Toppings:** {', '.join(item['toppings']) or 'None'}")
    st.write("All condiments and toppings are included.")


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
    st.markdown(f"**This burger and drink: {money(item_total(current_item))}**")
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
            f"— {money(item_total(item))}"
        )
        st.caption(
            f"{item['cheese'].title()} cheese · "
            f"Condiments: {', '.join(item['condiments']) or 'None'} · "
            f"Toppings: {', '.join(item['toppings']) or 'None'}"
        )
        if st.button("Remove", key=f"remove_cart_item_{index}"):
            cart.pop(index)
            st.rerun()

    cart_total = sum(item_total(item) for item in cart)
    st.markdown(f"### Current total: {money(cart_total)}")
    if st.button("Review order", type="primary"):
        customer_name = name.strip()
        customer_phone = normalize_phone(phone)
        if not customer_name:
            st.error("Enter your name to continue.")
        elif not 7 <= len(customer_phone) <= 15:
            st.error("Enter a valid phone number with 7 to 15 digits.")
        else:
            st.session_state.draft_order = {
                "name": customer_name,
                "phone": customer_phone,
                "items": [dict(item) for item in cart],
                "total": cart_total,
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
            f"Burger {index} and {item['drink_size']} drink: "
            f"{money(item_total(item))}"
        )
    st.markdown(f"### Total: {money(order['total'])}")
    st.info("Payment is due at pickup. No online payment is collected.")
    st.caption(
        f"Estimated pickup is about {PICKUP_ESTIMATE_MINUTES} minutes after "
        "confirmation. Actual timing may vary."
    )

    edit_column, confirm_column = st.columns(2)
    with edit_column:
        if st.button("Back to cart"):
            st.session_state.order_stage = "build"
            st.rerun()
    with confirm_column:
        if st.button("Confirm and place order", type="primary"):
            ordered_at = datetime.now().astimezone()
            confirmed_order = {
                **order,
                "order_id": uuid.uuid4().hex[:8].upper(),
                "ordered_at": ordered_at.isoformat(),
                "pickup_at": (
                    ordered_at + timedelta(minutes=PICKUP_ESTIMATE_MINUTES)
                ).isoformat(),
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
    st.markdown(f"### Total: {money(order['total'])}")
    st.write(
        "**Estimated pickup (may vary):** "
        + datetime.fromisoformat(order["pickup_at"]).strftime("%I:%M %p %Z")
    )
    st.info(
        "Pay at pickup. Please confirm the pickup location and current hours "
        "with LAC Burgers before traveling; those details are placeholders."
    )

    if st.button("Start another order"):
        for key in (
            "name",
            "phone",
            "size",
            "cheese",
            "drink",
            "drink_size",
        ):
            st.session_state.pop(key, None)
        for key in list(st.session_state):
            if key.startswith(("condiments_", "toppings_")):
                st.session_state.pop(key, None)
        st.session_state.order_stage = "build"
        st.session_state.cart = []
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
            st.markdown(f"**Order {order['order_id']} · {money(order['total'])}**")
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
    st.write("Build your burgers, review your order, and pay at pickup.")
    st.info(
        f"**Pickup address:** {PICKUP_ADDRESS}\n\n"
        f"**Restaurant hours:** {RESTAURANT_HOURS}\n\n"
        f"Pickup estimate: about {PICKUP_ESTIMATE_MINUTES} minutes after "
        "confirmation; actual timing may vary. This estimate does not check "
        "opening hours or live kitchen capacity, and no pickup time is reserved."
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
