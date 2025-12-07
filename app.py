# app.py
import streamlit as st
import json
from predict import predict_breed
from pathlib import Path

# --- load CSS helper ---
def load_css():
    css = Path("assets/god_ui.css").read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# --- load data ---
breed_raw = json.load(open("data/120_breeds_new[1].json"))
breed_info = {b["Breed"].lower(): b for b in breed_raw}

# Page config
st.set_page_config(page_title="DogBreed AI — Pro", page_icon="🐶", layout="wide")

load_css()

# Header (gradient + logo)
col1, col2 = st.columns([1, 5])
with col1:
    st.image("assets/logo.png", width=80)
with col2:
    st.markdown("""
    <div class="hero">
      <h1 class="glow">DogBreed AI — Pro</h1>
      <p class="sub">Instant breed detection • Vet-style tips • Breed store • Local chatbot</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---", unsafe_allow_html=True)

# Main card
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("### Upload a clear photo of the dog (face or full body)")

uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"])
if uploaded_file:
    st.image(uploaded_file, width=350, caption="Uploaded image")
    uploaded_file.seek(0)
    breed, confidence = predict_breed(uploaded_file)
    breed_l = breed.lower()
    st.markdown(f"""
      <div class="result-row">
        <div class="result-left">
          <h2>{breed.replace('_',' ').title()}</h2>
          <div class="pill">Confidence: {confidence:.2f}</div>
        </div>
        <div class="result-right">
          <a class="btn" href="/#/pages/2_Breed_Details.py">View Breed Details</a>
          <a class="btn ghost" href="/#/pages/3_Food_Store.py">Open Store</a>
        </div>
      </div>
    """, unsafe_allow_html=True)
else:
    st.write("Tip: take a close photo of the dog's face for best results.")
st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown('<div class="footer">Built with ❤️ • DogBreed AI Pro</div>', unsafe_allow_html=True)
