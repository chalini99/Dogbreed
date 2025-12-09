import streamlit as st
from predict import predict_breed
import json
from chatbot import ask_bot
import os
import razorpay
import uuid

# -----------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------
st.set_page_config(page_title="DogBreed AI", page_icon="🐶", layout="wide")

# -----------------------------------------------------
# LOAD JSON
# -----------------------------------------------------
breed_raw = json.load(open("data/120_breeds_new[1].json"))
diet_raw = json.load(open("data/120_diet_plans[1].json"))
dogfood_data = json.load(open("data/dogfood.json"))

breed_info = {item["Breed"].lower(): item for item in breed_raw}
diet_info  = {item["name"].lower(): item["diet_plan"] for item in diet_raw}

# -----------------------------------------------------
# RAZORPAY CONFIG
# -----------------------------------------------------
RAZOR_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZOR_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

razor_client = razorpay.Client(auth=(RAZOR_KEY_ID, RAZOR_KEY_SECRET)) if RAZOR_KEY_ID else None


# -----------------------------------------------------
# STORE FUNCTIONS
# -----------------------------------------------------
def get_products_for_breed(breed_key):
    return dogfood_data.get(breed_key, [])

def add_to_cart(product):
    st.session_state.setdefault("cart", []).append(product)

def cart_total_in_paise():
    return sum(i["price_inr"] for i in st.session_state.get("cart", [])) * 100

def clear_cart():
    st.session_state["cart"] = []

def create_razorpay_order(amount_paise):
    return razor_client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"rcpt_{uuid.uuid4().hex[:10]}",
        "payment_capture": 1
    })

def show_food_products(breed_key):
    st.markdown("### 🛒 Recommended Products")
    products = get_products_for_breed(breed_key)

    if not products:
        st.info("No food available.")
        return

    for p in products:
        col1, col2 = st.columns([1, 3])
        with col1: st.image(p["image"], width=130)
        with col2:
            st.subheader(p["name"])
            st.write(p["description"])
            st.write(f"**Price:** ₹{p['price_inr']}")
            if st.button("Add to Cart", key=p["id"]):
                add_to_cart(p)
                st.success("Added to cart!")

def show_cart_sidebar():
    st.sidebar.markdown("## 🧺 Cart")
    cart = st.session_state.get("cart", [])

    if not cart:
        st.sidebar.write("Cart is empty")
        return

    for item in cart:
        st.sidebar.write(f"{item['name']} — ₹{item['price_inr']}")

    st.sidebar.write(f"**Total: ₹{cart_total_in_paise()/100:.2f}**")

    if st.sidebar.button("Checkout"):
        st.session_state["checkout"] = True

# -----------------------------------------------------
# CHECKOUT UI
# -----------------------------------------------------
def show_checkout_page():
    st.markdown("## Checkout")

    cart = st.session_state.get("cart", [])
    if not cart:
        st.info("Cart empty.")
        return

    total_paise = cart_total_in_paise()
    st.write(f"Total: **₹{total_paise/100:.2f}**")

    if not razor_client:
        st.error("Razorpay keys missing.")
        return

    order = create_razorpay_order(total_paise)

    name = st.text_input("Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")

    if st.button("Pay Now"):
        st.markdown(f"""
        <script src="https://checkout.razorpay.com/v1/checkout.js"
            data-key="{RAZOR_KEY_ID}"
            data-amount="{total_paise}"
            data-currency="INR"
            data-order_id="{order['id']}"
            data-name="DogBreed Store"
            data-prefill.name="{name}"
            data-prefill.email="{email}"
            data-prefill.contact="{phone}">
        </script>
        """, unsafe_allow_html=True)
        st.success("Payment window opened!")

    if st.button("Clear Cart"):
        clear_cart()
        st.rerun()


# -----------------------------------------------------
# SIDEBAR NAVIGATION  (FIXED)
# -----------------------------------------------------
st.sidebar.title("🐾 Navigation")
page = st.sidebar.radio("Go to:", ["Prediction", "Chatbot"])

show_cart_sidebar()

# -----------------------------------------------------
# PAGE: PREDICTION
# -----------------------------------------------------
if page == "Prediction":

    st.title("🐶 DogBreed Prediction")

    uploaded_file = st.file_uploader("Upload dog image", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        col1, col2 = st.columns([1,2])

        with col1: st.image(uploaded_file, width=350)

        uploaded_file.seek(0)
        breed, conf = predict_breed(uploaded_file)
        breed_l = breed.lower()

        with col2:
            st.subheader(f"🎯 Prediction: {breed}")
            st.write(f"Confidence: {conf:.2f}")

        st.markdown("### 📌 Breed Info")
        st.write(breed_info.get(breed_l, "No info available."))

        st.markdown("### 🍖 Diet Plan")
        st.write(diet_info.get(breed_l, "No diet info."))

        show_food_products(breed_l)

        if st.session_state.get("checkout"):
            show_checkout_page()

# -----------------------------------------------------
# PAGE: CHATBOT
# -----------------------------------------------------
elif page == "Chatbot":
    st.title("💬 DogBreed Chatbot")

    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("chat_input_key", 0)

    for msg in st.session_state.chat_history:
        role = "You" if msg["role"] == "user" else "🐶 DogBot"
        color = "#2b2b2b" if msg["role"] == "user" else "#1f2937"
        st.markdown(f"""
        <div style="padding:10px; background:{color}; border-radius:8px; margin:5px">
        <b>{role}:</b> {msg['content']}
        </div>
        """, unsafe_allow_html=True)

    user_q = st.text_input("Ask something 👇", key=f"chat_{st.session_state.chat_input_key}")

    if user_q:
        st.session_state.chat_history.append({"role": "user", "content": user_q})
        bot_reply = ask_bot(user_q)
        st.session_state.chat_history.append({"role": "bot", "content": bot_reply})
        st.session_state.chat_input_key += 1
        st.rerun()
