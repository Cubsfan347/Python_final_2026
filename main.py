import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st


MENU_PATH = Path(__file__).with_name("menu.txt")
ORDERS_PATH = Path(__file__).with_name("orders.jsonl")
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
    "size",
    "cheese",
    "condiments",
    "toppings",
    "drink",
    "drink_size",
    "total",
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


def order_summary(order: dict) -> None:
    st.write(f"**{order['size'].title()} burger** with {order['cheese']}")
    st.write(f"**Drink:** {order['drink'].title()} ({order['drink_size']})")
    st.write(f"**Condiments:** {', '.join(order['condiments']) or 'None'}")
    st.write(f"**Toppings:** {', '.join(order['toppings']) or 'None'}")
    st.write("All condiments and toppings are included.")


def render_order_form(menu: dict[str, list[str]]) -> None:
    if st.session_state.pop("restore_draft", False):
        draft = st.session_state.get("draft_order", {})
        for key in ("name", "phone", "size", "cheese", "drink", "drink_size"):
            if key in draft:
                st.session_state[key] = draft[key]
        for category in ("condiments", "toppings"):
            selected = set(draft.get(category, []))
            for index, choice in enumerate(menu[category.upper()]):
                st.session_state[f"{category}_{index}"] = choice in selected

    with st.form("order_form"):
        st.subheader("Your details")
        name = st.text_input("Name", key="name", max_chars=80)
        phone = st.text_input(
            "Phone number",
            key="phone",
            help="Used to look up your recent orders.",
            max_chars=24,
        )

        st.subheader("Build your burger")
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
            drink_size = st.selectbox(
                "Drink size", menu["DRINK_SIZE"], key="drink_size"
            )

        submitted = st.form_submit_button("Review order", type="primary")

    if submitted:
        customer_name = name.strip()
        customer_phone = normalize_phone(phone)
        if not customer_name:
            st.error("Enter your name to continue.")
        elif not 7 <= len(customer_phone) <= 15:
            st.error("Enter a valid phone number with 7 to 15 digits.")
        elif size.lower() not in BURGER_PRICES:
            st.error(f"No price is configured for the {size} burger.")
        elif drink_size.lower() not in DRINK_PRICES:
            st.error(f"No price is configured for a {drink_size} drink.")
        else:
            st.session_state.draft_order = {
                "name": customer_name,
                "phone": customer_phone,
                "size": size,
                "cheese": cheese,
                "condiments": condiments,
                "toppings": toppings,
                "drink": drink,
                "drink_size": drink_size,
                "total": BURGER_PRICES[size.lower()] + DRINK_PRICES[drink_size.lower()],
            }
            st.session_state.order_stage = "review"
            st.rerun()


def render_review() -> None:
    order = st.session_state.draft_order
    st.subheader("Review your order")
    st.caption(f"Customer: {order['name']} · Phone: {order['phone']}")
    order_summary(order)

    price_column, amount_column = st.columns([3, 1])
    with price_column:
        st.write(f"{order['size'].title()} burger")
        st.write(f"{order['drink_size'].title()} drink")
    with amount_column:
        st.write(money(BURGER_PRICES[order["size"].lower()]))
        st.write(money(DRINK_PRICES[order["drink_size"].lower()]))
    st.markdown(f"### Total: {money(order['total'])}")
    st.info("Payment is due at pickup. No online payment is collected.")

    edit_column, confirm_column = st.columns(2)
    with edit_column:
        if st.button("Edit order"):
            st.session_state.restore_draft = True
            st.session_state.order_stage = "build"
            st.rerun()
    with confirm_column:
        if st.button("Confirm and place order", type="primary"):
            ordered_at = datetime.now().astimezone()
            confirmed_order = {
                **order,
                "order_id": uuid.uuid4().hex[:8].upper(),
                "ordered_at": ordered_at.isoformat(),
                "pickup_at": (ordered_at + timedelta(minutes=20)).isoformat(),
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
        "**Estimated pickup:** "
        + datetime.fromisoformat(order["pickup_at"]).strftime("%I:%M %p %Z")
    )
    st.info("Pay at pickup. Your order history is saved locally for this demo.")

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
    st.set_page_config(page_title="Burger Order", page_icon="🍔", layout="centered")
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
    st.title("Burger Order")
    st.write("Build your meal, review it, and pay when you pick it up.")
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
