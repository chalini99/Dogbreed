import streamlit as st
from predict import predict_breed
import json
from chatbot import ask_bot
import os
import razorpay
import uuid

#────────────────────────────────────────
# LOAD JSON DATA
#────────────────────────────────────────
breed_raw = json.load(open(r"data/120_breeds_new[1].json"))
diet_raw = json.load(open(r"data/120_diet_plans[1].json"))
dogfood_data = json.load(open(r"data/dogfood.json"))

breed_info = {item["Breed"].lower(): item for item in breed_raw}
diet_info = {item["name"].lower(): item["diet_plan"] for item in diet_raw}

#────────────────────────────────────────
# RAZORPAY CONFIG
#────────────────────────────────────────
RAZOR_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZOR_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if RAZOR_KEY_ID and RAZOR_KEY_SECRET:
    razor_client = razorpay.Client(auth=(RAZOR_KEY_ID, RAZOR_KEY_SECRET))
else:
    razor_client = None


#────────────────────────────────────────
# STORE FUNCTIONS
#────────────────────────────────────────
def get_products_for_breed(breed_key):
    return dogfood_data.get(breed_key, [])


def add_to_cart(product):
    if "cart" not in st.session_state:
        st.session_state.cart = []
    st.session_state.cart.append(product)


def cart_total_in_paise():
    if "cart" not in st.session_state:
        return 0
    total_inr = sum(item["price_inr"] for item in st.session_state.cart)
    return total_inr * 100


def clear_cart():
    st.session_state.cart = []


def create_razorpay_order(amount_paise):
    if not razor_client:
        raise RuntimeError("Razorpay not configured.")
    order = razor_client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"rcpt_{uuid.uuid4().hex[:10]}",
        "payment_capture": 1
    })
    return order


def show_food_products(breed_key):
    st.markdown("### 🛒 Recommended Food Products")

    products = get_products_for_breed(breed_key)
    if not products:
        st.info("No food products available for this breed.")
        return

    for p in products:
        col_img, col_info = st.columns([1, 3])

        with col_img:
            st.image(p["image"], width=130)

        with col_info:
            st.subheader(p["name"])
            st.write(p["description"])
            st.write(f"**Price:** ₹{p['price_inr']}")

            if st.button("Add to Cart", key=f"add_{p['id']}"):
                add_to_cart(p)
                st.success("Added to cart!")

    st.markdown("---")


def show_cart_sidebar():
    st.sidebar.markdown("## 🧺 Cart")

    cart = st.session_state.get("cart", [])

    if len(cart) == 0:
        st.sidebar.write("Cart is empty")
        return

    for item in cart:
        st.sidebar.write(f"{item['name']} — ₹{item['price_inr']}")

    total = cart_total_in_paise() / 100
    st.sidebar.write(f"**Total: ₹{total:.2f}**")

    if st.sidebar.button("Checkout"):
        st.session_state.show_checkout = True


def show_checkout_page():
    st.markdown("## Checkout")

    cart = st.session_state.get("cart", [])
    if len(cart) == 0:
        st.info("Cart empty.")
        return

    total_paise = cart_total_in_paise()
    total_inr = total_paise / 100
    st.write(f"Total amount: **₹{total_inr:.2f}**")

    if not razor_client:
        st.error("Razorpay keys missing.")
        return

    order = create_razorpay_order(total_paise)

    name = st.text_input("Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")

    if st.button("Pay with Razorpay"):
        checkout_html = f"""
        <script src="https://checkout.razorpay.com/v1/checkout.js"
            data-key="{RAZOR_KEY_ID}"
            data-amount="{total_paise}"
            data-currency="INR"
            data-order_id="{order['id']}"
            data-name="DogBreed Store"
            data-description="Dog Food Purchase"
            data-prefill.name="{name}"
            data-prefill.email="{email}"
            data-prefill.contact="{phone}">
        </script>
        """
        st.markdown(checkout_html, unsafe_allow_html=True)
        st.success("Payment window opened!")

    if st.button("Clear Cart"):
        clear_cart()
        st.rerun()



#────────────────────────────────────────
# SIDEBAR NAVIGATION
#────────────────────────────────────────
st.sidebar.title("🐾 Navigation")
page = st.sidebar.radio("Go to:", [" Prediction", " Chatbot"])

show_cart_sidebar()


#────────────────────────────────────────
# PAGE: PREDICTION (FIXED)
#────────────────────────────────────────
if page == " Prediction":
    st.title("🐶 DogBreed AI Dashboard")
    st.write("Upload a dog image to get prediction + breed info + diet + food store!")

    uploaded_file = st.file_uploader("Upload dog image", type=["jpg", "png", "jpeg"])

    if uploaded_file:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image(uploaded_file, width=350)

        uploaded_file.seek(0)
        breed, confidence = predict_breed(uploaded_file)
        breed_l = breed.lower()

        with col2:
            st.subheader(f"🎯 Prediction: {breed}")
            st.write(f"Confidence: {confidence:.2f}")

        st.markdown("### 📌 Breed Information")
        st.write(breed_info.get(breed_l, "No info available."))

        st.markdown("### 🍖 Diet Plan")
        st.write(diet_info.get(breed_l, "No diet info."))

        show_food_products(breed_l)

        if st.session_state.get("show_checkout"):
            show_checkout_page()


#────────────────────────────────────────
# PAGE: CHATBOT (WORKING NOW)
#────────────────────────────────────────
elif page == "📘 Chatbot":
    st.title("💬 DogBreed Assistant")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "input_key" not in st.session_state:
        st.session_state.input_key = 0

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(
                f"""
                <div style="text-align:right; background:#2b2b2b; padding:10px;
                border-radius:8px; margin:5px;"><b>You:</b> {msg['content']}</div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="background:#1f2937; padding:10px;
                border-radius:8px; margin:5px;"><b>🐶 DogBot:</b> {msg['content']}</div>
                """,
                unsafe_allow_html=True
            )

    user_q = st.text_input("Ask something 👇", key=f"input_{st.session_state.input_key}")

    if user_q:
        st.session_state.chat_history.append({"role": "user", "content": user_q})
        bot_reply = ask_bot(user_q)
        st.session_state.chat_history.append({"role": "bot", "content": bot_reply})
        st.session_state.input_key += 1
        st.rerun()
