import streamlit as st
import matplotlib.pyplot as plt
import google.generativeai as genai
import os
from dotenv import load_dotenv

# -------------------------
# Setup Gemini
# -------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")

st.set_page_config(page_title="GluCoffee", layout="wide")

# -------------------------
# Sidebar Navigasi (Interaktif + Estetik)
# -------------------------
st.sidebar.markdown("""
<style>
.sidebar-menu {
    font-size: 16px;
    padding-top: 10px;
}
.menu-button {
    display: block;
    margin-bottom: 10px;
    padding: 10px 14px;
    border: 1px solid #ddd;
    border-radius: 10px;
    background-color: white;
    color: #333;
    text-decoration: none;
    transition: all 0.2s ease;
    font-weight: 500;
}
.menu-button:hover {
    background-color: #f7f7f7;
    border-color: #bbb;
    color: #C27A48;
}
.menu-button.active {
    background-color: #FFECD1;
    border-color: #C27A48;
    color: #C27A48;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# Inisialisasi halaman aktif
if "active_page" not in st.session_state:
    st.session_state.active_page = "🏠 Home"

# Fungsi render menu sidebar (tanpa duplikasi)
def menu_item(label, icon):
    page_key = f"{icon} {label}"
    active = st.session_state.active_page == page_key
    css_class = "menu-button active" if active else "menu-button"

    with st.sidebar.form(key=f"form_{label}", clear_on_submit=False):
        clicked = st.form_submit_button(f"{icon} {label}")
        if clicked:
            st.session_state.active_page = page_key
        st.markdown(f'<div class="{css_class}">{icon} {label}</div>', unsafe_allow_html=True)

# Render menu sidebar (tanpa dobel)
st.sidebar.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)
menu_item("Home", "🏠")
menu_item("FINDRISC", "📋")
menu_item("Konsumsi Kopi", "☕")
menu_item("Hasil Analisis", "📊")
st.sidebar.markdown("</div>", unsafe_allow_html=True)

menu = st.session_state.active_page

# -------------------------
# Inisialisasi session_state
# -------------------------
for key in ["findrisc_score", "findrisc_risk", "total_sugar", "coffee_type"]:
    if key not in st.session_state:
        st.session_state[key] = None

# -------------------------
# Halaman 1: Home
# -------------------------
if menu == "🏠 Home":
    st.title("☕ GluCoffee – Start Your Awareness with a Cup of Coffee")
    st.markdown("""
    Selamat datang di **GluCoffee**!
    Platform ini membantu kamu memahami risiko diabetes berdasarkan:
    - 📋 **Tes FINDRISC**
    - ☕ **Analisis konsumsi kopi dan gula harian**

    Pilih menu di sidebar untuk memulai.
    """)

# -------------------------
# Halaman 2: FINDRISC
# -------------------------
elif menu == "📋 FINDRISC":
    st.header("📋 Kuisioner FINDRISC")

    col1, col2 = st.columns(2)
    with col1:
        usia = st.selectbox("Usia Anda:", ["<45 tahun", "45–54 tahun", "55–64 tahun", ">64 tahun"])
        bmi = st.selectbox("BMI Anda:", ["<25", "25–30", ">30"])
        lingkar_perut = st.selectbox("Lingkar perut:", [
            "<80 cm (pria) / <94 cm (wanita)",
            "80–88 cm (wanita) / 94–102 cm (pria)",
            ">88 cm (wanita) / >102 cm (pria)"
        ])
    with col2:
        aktifitas = st.selectbox("Apakah Anda berolahraga ≥30 menit/hari?", ["Ya", "Tidak"])
        makan_sayur = st.selectbox("Apakah Anda makan sayur/buah setiap hari?", ["Ya", "Tidak"])
        pernah_gula_tinggi = st.selectbox("Pernah diberi tahu kadar gula tinggi?", ["Ya", "Tidak"])
        keluarga_dm = st.selectbox("Apakah ada keluarga dengan diabetes?",
                                   ["Tidak", "Keluarga jauh", "Orang tua/sodara kandung"])

    if st.button("💾 Simpan Hasil FINDRISC"):
        skor = 0
        skor += {"<45 tahun": 0, "45–54 tahun": 2, "55–64 tahun": 3, ">64 tahun": 4}[usia]
        skor += {"<25": 0, "25–30": 1, ">30": 3}[bmi]
        skor += {"<80 cm (pria) / <94 cm (wanita)": 0,
                 "80–88 cm (wanita) / 94–102 cm (pria)": 3,
                 ">88 cm (wanita) / >102 cm (pria)": 4}[lingkar_perut]
        skor += 0 if aktifitas == "Ya" else 2
        skor += 0 if makan_sayur == "Ya" else 1
        skor += 5 if pernah_gula_tinggi == "Ya" else 0
        skor += {"Tidak": 0, "Keluarga jauh": 3, "Orang tua/sodara kandung": 5}[keluarga_dm]

        risiko = (
            "Rendah" if skor < 7 else
            "Sedang" if skor < 12 else
            "Tinggi" if skor < 15 else
            "Sangat Tinggi"
        )

        st.session_state.findrisc_score = skor
        st.session_state.findrisc_risk = risiko

        st.success(f"Skor FINDRISC Anda: **{skor}** → Risiko **{risiko}** tersimpan.")

# -------------------------
# Halaman 3: Konsumsi Kopi
# -------------------------
elif menu == "☕ Konsumsi Kopi":
    st.header("☕ Analisis Konsumsi Kopi")

    coffee_options = [
        "Kopi Kenangan Mantan",
        "Kopi Susu",
        "Kopi Susu Black Aren",
        "Salted Caramel Macchiato",
        "Caffe Latte",
        "Matcha Latte",
        "Butterscotch Latte",
        "Americano",
        "Doubleshot Espresso Latte",
        "Vanilla Latte Caffe Mocha",
        "Aren Latte",
        "Iced Buttercream Latte",
        "Soy Matcha Latte",
        "Cappuccino"
    ]

    coffee_type = st.selectbox("Jenis Kopi:", coffee_options)
    volume_ml = st.radio("Ukuran Gelas:", ["15 oz (≈444 ml)", "16 oz (≈473 ml)"])
    jumlah_gelas = st.number_input("Jumlah Gelas Hari Ini:", min_value=1, max_value=10, value=1, step=1)
    topping = st.multiselect("Topping Tambahan:", [
        "Nata De Coco", "Salted Caramel", "Whipped Cream", "Brown Sugar Jelly", "Oatmilk"
    ])

    if st.button("💾 Simpan Konsumsi Kopi"):
        sugar_map = {
            "Kopi Kenangan Mantan": 16.0,
            "Kopi Susu": 9.5,
            "Kopi Susu Black Aren": 14.0,
            "Salted Caramel Macchiato": 28.0,
            "Caffe Latte": 31.5,
            "Matcha Latte": 17.5,
            "Butterscotch Latte": 24.4,
            "Americano": 0.0,
            "Doubleshot Espresso Latte": 25.5,
            "Vanilla Latte Caffe Mocha": 25.7,
            "Aren Latte": 21.0,
            "Iced Buttercream Latte": 31.5,
            "Soy Matcha Latte": 36.8,
            "Cappuccino": 13.6
        }

        volume_value = 444 if "15 oz" in volume_ml else 473
        sugar_per_cup = sugar_map.get(coffee_type, 15) * (volume_value / 350)
        total_sugar = sugar_per_cup * jumlah_gelas + len(topping) * 5

        st.session_state.total_sugar = total_sugar
        st.session_state.coffee_type = coffee_type

        st.success(f"Total gula dari kopi: **{total_sugar:.1f} gram** (tersimpan).")

# -------------------------
# Halaman 4: Hasil Analisis
# -------------------------
elif menu == "📊 Hasil Analisis":
    st.markdown("## 📊 Ringkasan & Rekomendasi dari Gemini")

    if st.session_state.findrisc_score or st.session_state.total_sugar:
        if st.session_state.findrisc_score:
            st.info(f"**Skor FINDRISC:** {st.session_state.findrisc_score} ({st.session_state.findrisc_risk})")
        if st.session_state.total_sugar:
            total_sugar = st.session_state.total_sugar
            st.info(f"**Total Gula dari Kopi:** {total_sugar:.1f} gram")

            batas_harian = 50
            persen_gula = min(total_sugar / batas_harian * 100, 100)
            sisa = max(batas_harian - total_sugar, 0)

            labels = ['Gula dari Kopi', 'Sisa Batas Harian']
            sizes = [total_sugar, sisa]
            colors = ['orange', 'lightgray']

            fig, ax = plt.subplots()
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                textprops={'color': 'black'}
            )
            ax.axis('equal')
            st.pyplot(fig)

            if total_sugar > batas_harian:
                st.error(f"⚠️ Konsumsi gula dari kopi telah **melebihi batas harian (50 gram)**.")
            else:
                st.success(f"✅ Kamu telah mengonsumsi **{persen_gula:.1f}%** dari batas harian gula (50 gram).")

        prompt = f"""
        Seseorang memiliki skor FINDRISC {st.session_state.findrisc_score} dengan risiko {st.session_state.findrisc_risk},
        dan mengonsumsi {st.session_state.total_sugar:.1f} gram gula dari kopi hari ini (batas 50 gram/hari).
        Berikan analisis singkat tentang risiko kesehatannya dan saran gaya hidup sehat yang ramah dan mudah dipahami.
        """

        with st.spinner("💡 Gemini sedang menganalisis..."):
            response = model.generate_content(prompt)
            st.markdown("### 💬 Rekomendasi Gemini:")
            st.write(response.text)
    else:
        st.warning("Belum ada data FINDRISC atau konsumsi kopi yang tersimpan. Silakan isi dari menu lain terlebih dahulu.")
