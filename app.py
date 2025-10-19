import streamlit as st
import matplotlib.pyplot as plt
import google.generativeai as genai
import json
import os
import hashlib
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

# -------------------------
# Konfigurasi Awal
# -------------------------
st.set_page_config(
    page_title="GluCoffee - Diabetes Risk Tracker",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Setup Gemini AI
load_dotenv()

# Load API Key dari secrets.toml (Streamlit Cloud) atau .env (Local)
try:
    # Coba ambil dari st.secrets (prioritas utama)
    API_KEY = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
except:
    # Fallback ke environment variable
    API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("API Key tidak ditemukan! Tambahkan GEMINI_API_KEY atau GOOGLE_API_KEY di .streamlit/secrets.toml atau .env")
    model = None
else:
    genai.configure(api_key=API_KEY)
    
    # Gunakan Gemini 2.0 Flash (model terbaru dan tercepat)
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
    except:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
        except:
            try:
                model = genai.GenerativeModel("gemini-pro")
            except:
                model = None
                st.error("Model AI tidak dapat dimuat. Periksa API key Anda.")

# -------------------------
# User ID Management (Browser-specific)
# -------------------------
def get_browser_id():
    """Generate unique ID based on browser session"""
    # Streamlit akan membuat session baru untuk setiap browser/tab
    if 'browser_id' not in st.session_state:
        # Generate unique ID untuk session ini
        st.session_state.browser_id = hashlib.md5(
            str(datetime.now().timestamp()).encode()
        ).hexdigest()[:12]
    return st.session_state.browser_id

# -------------------------
# Database JSON Sederhana
# -------------------------
DATA_FOLDER = "glucoffee_users"
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

def get_user_file():
    """Get data file path untuk user ini"""
    browser_id = get_browser_id()
    return os.path.join(DATA_FOLDER, f"user_{browser_id}.json")

def load_data():
    """Memuat data dari file JSON"""
    user_file = get_user_file()
    if os.path.exists(user_file):
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return init_data_structure()
    return init_data_structure()

def init_data_structure():
    """Struktur data awal"""
    return {
        "user_profile": {
            "name": None,
            "created_at": None
        },
        "findrisc": {
            "score": None,
            "risk_level": None,
            "last_updated": None,
            "raw_answers": {}
        },
        "coffee_history": []
    }

def save_data(data):
    """Menyimpan data ke file JSON"""
    user_file = get_user_file()
    with open(user_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Load data
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# -------------------------
# Styling CSS
# -------------------------
st.markdown("""
<style>
    .sidebar-menu {
        font-size: 16px;
        padding: 10px 0;
    }
    
    .info-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    
    .warning-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    
    .success-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 50px;
        font-weight: 600;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Sidebar Navigation
# -------------------------
st.sidebar.title("☕ GluCoffee")
st.sidebar.markdown("---")

# User Profile Section
data = st.session_state.data
if data['user_profile']['name']:
    st.sidebar.success(f"👤 {data['user_profile']['name']}")
    if data['findrisc']['last_updated']:
        last_test = datetime.fromisoformat(data['findrisc']['last_updated'])
        days_ago = (datetime.now() - last_test).days
        st.sidebar.caption(f"FINDRISC terakhir: {days_ago} hari lalu")
else:
    st.sidebar.info("Belum ada profil")

st.sidebar.markdown("---")

# Navigation Menu - Updated
menu_options = {
    "🏠 Home": "home",
    "📋 Tes FINDRISC": "findrisc",
    "☕ Konsumsi Kopi": "coffee",
    "📊 Hasil Analisis": "analysis"
}

if 'active_page' not in st.session_state:
    st.session_state.active_page = "home"

for label, page_key in menu_options.items():
    if st.sidebar.button(label, key=f"nav_{page_key}", use_container_width=True):
        st.session_state.active_page = page_key

st.sidebar.markdown("---")
st.sidebar.caption("Tips:")
st.sidebar.caption("- Tes FINDRISC cukup 1x/6 bulan")
st.sidebar.caption("- Catat kopi setiap hari")
st.sidebar.caption("- Cek analisis untuk rekomendasi")

# -------------------------
# Helper Functions
# -------------------------

def calculate_daily_sugar():
    """Hitung total gula hari ini"""
    today = date.today().isoformat()
    total = sum(
        entry['sugar'] 
        for entry in data['coffee_history'] 
        if entry['date'].startswith(today)
    )
    return total

def calculate_weekly_average():
    """Hitung rata-rata gula per hari minggu ini"""
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    
    recent_entries = [
        entry for entry in data['coffee_history']
        if datetime.fromisoformat(entry['date']) > week_ago
    ]
    
    if not recent_entries:
        return 0
    
    daily_totals = {}
    for entry in recent_entries:
        day = entry['date'].split('T')[0]
        daily_totals[day] = daily_totals.get(day, 0) + entry['sugar']
    
    return sum(daily_totals.values()) / len(daily_totals) if daily_totals else 0

def get_findrisc_status():
    """Cek status FINDRISC"""
    if not data['findrisc']['last_updated']:
        return "belum_isi", "Belum pernah diisi"
    
    last_test = datetime.fromisoformat(data['findrisc']['last_updated'])
    days_ago = (datetime.now() - last_test).days
    
    if days_ago > 180:
        return "perlu_update", f"Sudah {days_ago} hari (perlu update)"
    else:
        return "valid", f"Valid ({days_ago} hari lalu)"

# -------------------------
# PAGE: HOME
# -------------------------
if st.session_state.active_page == "home":
    st.title("☕ GluCoffee")
    st.subheader("Kesadaran Diabetes Dimulai dari Secangkir Kopi")
    
    # Setup Profil Section - Moved to Home
    if not data['user_profile']['name']:
        st.markdown("---")
        st.markdown("### Setup Profil Anda")
        st.info("Silakan masukkan nama Anda untuk memulai. Data Anda akan tersimpan untuk browser ini.")
        
        with st.form("profile_form"):
            name = st.text_input("Nama Lengkap:", placeholder="Contoh: Budi Santoso")
            
            submitted = st.form_submit_button("Mulai Menggunakan GluCoffee", use_container_width=True)
            
            if submitted:
                if name.strip():
                    data['user_profile']['name'] = name.strip()
                    data['user_profile']['created_at'] = datetime.now().isoformat()
                    save_data(data)
                    st.success(f"Selamat datang, {name}!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Nama tidak boleh kosong")
        st.stop()
    
    # Main Content (hanya tampil setelah profil dibuat)
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
        ### Selamat Datang, {data['user_profile']['name']}!
        
        **GluCoffee** adalah aplikasi edukasi kesehatan yang membantu Anda:
        
        1. **Evaluasi Risiko Diabetes** melalui tes FINDRISC (Finnish Diabetes Risk Score)
           - Tes internasional yang tervalidasi
           - Cukup diisi 1x setiap 6 bulan
           - Prediksi risiko 10 tahun ke depan
        
        2. **Tracking Konsumsi Gula Harian** dari kopi favorit Anda
           - Database 14+ jenis kopi populer
           - Perhitungan akurat berdasarkan ukuran & topping
           - Monitor batas aman 50g/hari (WHO)
        
        3. **Rekomendasi Personal dari AI**
           - Analisis holistik risiko Anda
           - Saran meal plan harian
           - Tips gaya hidup sehat
        
        ---
        
        ### Langkah Selanjutnya:
        """)
        
        findrisc_status, findrisc_msg = get_findrisc_status()
        if findrisc_status == "belum_isi":
            st.warning("**Langkah 1:** Isi Tes FINDRISC (hanya 2 menit)")
        elif findrisc_status == "perlu_update":
            st.info(f"**Langkah 1:** Tes FINDRISC Anda {findrisc_msg}, sebaiknya update lagi")
        else:
            st.success(f"Tes FINDRISC: {findrisc_msg}")
        
        st.info("**Langkah 2:** Catat kopi yang Anda minum hari ini di Konsumsi Kopi")
        st.info("**Langkah 3:** Lihat analisis lengkap di Hasil Analisis")
        
        # Reset Profile Option
        with st.expander("Pengaturan Profil"):
            st.caption(f"Profil dibuat pada: {data['user_profile']['created_at']}")
            st.caption(f"Browser ID: {get_browser_id()}")
            if st.button("Reset Semua Data"):
                if st.checkbox("Saya yakin ingin menghapus semua data"):
                    st.session_state.data = init_data_structure()
                    save_data(st.session_state.data)
                    st.success("Data berhasil direset!")
                    st.rerun()
    
    with col2:
        st.markdown("### Status Anda Hari Ini")
        
        today_sugar = calculate_daily_sugar()
        weekly_avg = calculate_weekly_average()
        
        st.metric(
            "Gula Hari Ini",
            f"{today_sugar:.1f}g",
            f"{today_sugar - 50:.1f}g dari batas" if today_sugar > 0 else "Belum ada data"
        )
        
        st.metric(
            "Rata-rata Minggu Ini",
            f"{weekly_avg:.1f}g/hari"
        )
        
        if data['findrisc']['score'] is not None:
            st.metric(
                "Skor FINDRISC",
                data['findrisc']['score'],
                data['findrisc']['risk_level']
            )
        
        if today_sugar > 0:
            progress = min(today_sugar / 50, 1.0)
            st.progress(progress)
            if today_sugar > 50:
                st.error("Melebihi batas harian!")
            elif today_sugar > 40:
                st.warning("Mendekati batas!")
            else:
                st.success("Masih aman")

# -------------------------
# PAGE: TES FINDRISC
# -------------------------
elif st.session_state.active_page == "findrisc":
    st.title("Tes Risiko Diabetes (FINDRISC)")
    
    if not data['user_profile']['name']:
        st.warning("Silakan setup profil terlebih dahulu di menu Home")
        st.stop()
    
    findrisc_status, findrisc_msg = get_findrisc_status()
    
    if findrisc_status == "valid":
        st.success(f"Tes FINDRISC Anda masih valid ({findrisc_msg})")
        st.info(f"**Skor Terakhir:** {data['findrisc']['score']} - **Risiko:** {data['findrisc']['risk_level']}")
        st.markdown("---")
        st.caption("Tes FINDRISC cukup diisi ulang setiap 6 bulan")
        
        if not st.checkbox("Saya ingin mengisi ulang tes FINDRISC"):
            st.stop()
    
    st.markdown("""
    **Finnish Diabetes Risk Score (FINDRISC)** adalah tes skrining yang divalidasi secara internasional 
    untuk memperkirakan risiko seseorang terkena diabetes tipe 2 dalam 10 tahun ke depan.
    
    **Petunjuk:**
    - Jawab semua pertanyaan dengan jujur
    - Tes memakan waktu sekitar 2-3 menit
    """)
    
    st.markdown("---")
    
    with st.form("findrisc_form"):
        st.subheader("Kuisioner FINDRISC")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Data Demografis")
            
            usia = st.selectbox(
                "1. Usia Anda:",
                ["Di bawah 45 tahun (0 poin)", 
                 "45–54 tahun (2 poin)", 
                 "55–64 tahun (3 poin)", 
                 "Di atas 64 tahun (4 poin)"]
            )
            
            bmi = st.selectbox(
                "2. Indeks Massa Tubuh (BMI):",
                ["Di bawah 25 kg/m² (0 poin)", 
                 "25–30 kg/m² (1 poin)", 
                 "Di atas 30 kg/m² (3 poin)"]
            )
            st.caption("BMI = Berat (kg) / Tinggi² (m)")
            
            lingkar_perut = st.selectbox(
                "3. Lingkar Perut:",
                ["Pria <94 cm / Wanita <80 cm (0 poin)",
                 "Pria 94–102 cm / Wanita 80–88 cm (3 poin)",
                 "Pria >102 cm / Wanita >88 cm (4 poin)"]
            )
            
            aktifitas = st.selectbox(
                "4. Apakah Anda berolahraga minimal 30 menit setiap hari?",
                ["Ya (0 poin)", "Tidak (2 poin)"]
            )
        
        with col2:
            st.markdown("#### Gaya Hidup & Riwayat")
            
            makan_sayur = st.selectbox(
                "5. Seberapa sering Anda makan sayur atau buah?",
                ["Setiap hari (0 poin)", "Tidak setiap hari (1 poin)"]
            )
            
            obat_hipertensi = st.selectbox(
                "6. Pernahkah Anda minum obat antihipertensi secara rutin?",
                ["Tidak (0 poin)", "Ya (2 poin)"]
            )
            
            pernah_gula_tinggi = st.selectbox(
                "7. Pernahkah Anda ditemukan memiliki kadar gula darah tinggi?",
                ["Tidak (0 poin)", "Ya (5 poin)"]
            )
            st.caption("(Saat medical check-up, kehamilan, atau sakit)")
            
            keluarga_dm = st.selectbox(
                "8. Apakah ada anggota keluarga yang menderita diabetes?",
                ["Tidak (0 poin)",
                 "Ya: Kakek/nenek, paman/bibi, sepupu (3 poin)",
                 "Ya: Orang tua, saudara kandung, anak (5 poin)"]
            )
        
        st.markdown("---")
        submitted = st.form_submit_button("Hitung & Simpan Hasil", use_container_width=True)
        
        if submitted:
            # Mapping skor - Fixed logic
            skor = 0
            
            # Usia
            if "Di bawah 45" in usia:
                skor += 0
            elif "45" in usia and "54" in usia:
                skor += 2
            elif "55" in usia and "64" in usia:
                skor += 3
            elif "Di atas 64" in usia:
                skor += 4
            
            # BMI
            if "Di bawah 25" in bmi:
                skor += 0
            elif "25" in bmi and "30" in bmi:
                skor += 1
            elif "Di atas 30" in bmi:
                skor += 3
            
            # Lingkar Perut
            if "<94" in lingkar_perut or "<80" in lingkar_perut:
                skor += 0
            elif "94" in lingkar_perut and "102" in lingkar_perut:
                skor += 3
            elif ">102" in lingkar_perut or ">88" in lingkar_perut:
                skor += 4
            
            # Aktivitas
            skor += 0 if "Ya" in aktifitas else 2
            
            # Makan Sayur
            skor += 0 if "Setiap hari" in makan_sayur else 1
            
            # Obat Hipertensi
            skor += 0 if "Tidak" in obat_hipertensi else 2
            
            # Gula Tinggi
            skor += 0 if "Tidak" in pernah_gula_tinggi else 5
            
            # Keluarga DM
            if "Tidak" in keluarga_dm:
                skor += 0
            elif "Kakek" in keluarga_dm:
                skor += 3
            elif "Orang tua" in keluarga_dm:
                skor += 5
            
            # Klasifikasi risiko
            if skor < 7:
                risiko = "Rendah"
                penjelasan = "1 dari 100 orang akan mengembangkan diabetes dalam 10 tahun"
                warna = "success"
            elif skor < 12:
                risiko = "Sedikit Meningkat"
                penjelasan = "1 dari 25 orang akan mengembangkan diabetes dalam 10 tahun"
                warna = "info"
            elif skor < 15:
                risiko = "Sedang"
                penjelasan = "1 dari 6 orang akan mengembangkan diabetes dalam 10 tahun"
                warna = "warning"
            elif skor < 20:
                risiko = "Tinggi"
                penjelasan = "1 dari 3 orang akan mengembangkan diabetes dalam 10 tahun"
                warna = "warning"
            else:
                risiko = "Sangat Tinggi"
                penjelasan = "1 dari 2 orang akan mengembangkan diabetes dalam 10 tahun"
                warna = "error"
            
            # Simpan data
            data['findrisc'] = {
                "score": skor,
                "risk_level": risiko,
                "last_updated": datetime.now().isoformat(),
                "raw_answers": {
                    "usia": usia,
                    "bmi": bmi,
                    "lingkar_perut": lingkar_perut,
                    "aktifitas": aktifitas,
                    "makan_sayur": makan_sayur,
                    "obat_hipertensi": obat_hipertensi,
                    "pernah_gula_tinggi": pernah_gula_tinggi,
                    "keluarga_dm": keluarga_dm
                }
            }
            save_data(data)
            
            st.success("Hasil FINDRISC berhasil disimpan!")
            st.balloons()
            
            # Tampilkan hasil
            if warna == "success":
                st.success(f"### Skor Anda: {skor} poin - Risiko **{risiko}**")
            elif warna == "info":
                st.info(f"### Skor Anda: {skor} poin - Risiko **{risiko}**")
            elif warna == "warning":
                st.warning(f"### Skor Anda: {skor} poin - Risiko **{risiko}**")
            else:
                st.error(f"### Skor Anda: {skor} poin - Risiko **{risiko}**")
            
            st.info(f"**Interpretasi:** {penjelasan}")
            
            st.markdown("---")
            st.markdown("### Apa Selanjutnya?")
            st.markdown("""
            1. **Catat konsumsi kopi Anda** di menu Konsumsi Kopi
            2. **Lihat analisis lengkap** di menu Hasil Analisis
            3. **Update tes ini** setiap 6 bulan
            """)

# -------------------------
# PAGE: KONSUMSI KOPI
# -------------------------
elif st.session_state.active_page == "coffee":
    st.title("Catat Konsumsi Kopi Harian")
    
    if not data['user_profile']['name']:
        st.warning("Silakan setup profil terlebih dahulu di menu Home")
        st.stop()
    
    today_sugar = calculate_daily_sugar()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Gula Hari Ini", f"{today_sugar:.1f}g")
    col2.metric("Batas Aman (WHO)", "50g/hari")
    col3.metric("Sisa Kuota", f"{max(0, 50-today_sugar):.1f}g")
    
    if today_sugar > 50:
        st.error("PERINGATAN: Anda sudah melebihi batas aman konsumsi gula harian!")
    elif today_sugar > 40:
        st.warning("Mendekati batas!")
    
    st.markdown("---")
    
    coffee_database = {
        "Kopi Kenangan Mantan": 16.0,
        "Kopi Susu": 9.5,
        "Kopi Susu Black Aren": 14.0,
        "Salted Caramel Macchiato": 28.0,
        "Caffe Latte": 31.5,
        "Matcha Latte": 17.5,
        "Butterscotch Latte": 24.4,
        "Americano": 0.0,
        "Doubleshot Espresso Latte": 25.5,
        "Vanilla Latte": 25.7,
        "Caffe Mocha": 25.7,
        "Aren Latte": 21.0,
        "Iced Buttercream Latte": 31.5,
        "Soy Matcha Latte": 36.8,
        "Cappuccino": 13.6
    }
    
    with st.form("coffee_form"):
        st.subheader("Detail Konsumsi Kopi")
        
        col1, col2 = st.columns(2)
        
        with col1:
            coffee_type = st.selectbox(
                "Jenis Kopi:",
                options=list(coffee_database.keys())
            )
            
            base_sugar = coffee_database[coffee_type]
            if base_sugar == 0:
                st.info("Americano tidak mengandung gula tambahan!")
            else:
                st.info(f"Kandungan gula base: **{base_sugar}g** (reguler ~350ml)")
            
            volume = st.radio(
                "Ukuran Gelas:",
                ["Reguler (≈350ml)", "Large (≈473ml)"],
                horizontal=True
            )
        
        with col2:
            quantity = st.number_input(
                "Jumlah Gelas:",
                min_value=1,
                max_value=10,
                value=1
            )
            
            topping = st.multiselect(
                "Topping Tambahan:",
                ["Nata De Coco (+5g)", 
                 "Salted Caramel (+5g)", 
                 "Whipped Cream (+5g)", 
                 "Brown Sugar Jelly (+5g)", 
                 "Oatmilk (+3g)",
                 "Extra Shot Espresso (+0g)"]
            )
        
        volume_multiplier = 1.0 if "Reguler" in volume else 1.35
        sugar_per_cup = base_sugar * volume_multiplier
        topping_sugar = len(topping) * 5
        total_sugar = (sugar_per_cup * quantity) + topping_sugar
        
        st.markdown("---")
        st.markdown("### Estimasi Total")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Per Gelas", f"{sugar_per_cup:.1f}g")
        col2.metric("Topping", f"{topping_sugar}g")
        col3.metric("TOTAL", f"{total_sugar:.1f}g")
        
        submitted = st.form_submit_button("Simpan Konsumsi", use_container_width=True)
        
        if submitted:
            entry = {
                "date": datetime.now().isoformat(),
                "drink": coffee_type,
                "volume": volume,
                "quantity": quantity,
                "topping": topping,
                "sugar": total_sugar
            }
            
            data['coffee_history'].append(entry)
            save_data(data)
            
            st.success(f"Konsumsi kopi berhasil dicatat! Total gula: **{total_sugar:.1f}g**")
            st.balloons()
            
            new_total = today_sugar + total_sugar
            if new_total > 50:
                st.error(f"Total gula hari ini: **{new_total:.1f}g** (melebihi batas)")
    
    # Riwayat hari ini
    if data['coffee_history']:
        st.markdown("---")
        st.subheader("Riwayat Konsumsi Hari Ini")
        
        today_entries = [
            entry for entry in data['coffee_history']
            if entry['date'].startswith(date.today().isoformat())
        ]
        
        if today_entries:
            for i, entry in enumerate(reversed(today_entries), 1):
                time_str = datetime.fromisoformat(entry['date']).strftime("%H:%M")
                topping_str = ", ".join([t.split("(")[0].strip() for t in entry['topping']]) if entry['topping'] else "-"
                
                with st.expander(f"#{i} • {time_str} • {entry['drink']} • {entry['sugar']:.1f}g"):
                    col1, col2 = st.columns(2)
                    col1.write(f"**Ukuran:** {entry['volume']}")
                    col1.write(f"**Jumlah:** {entry['quantity']} gelas")
                    col2.write(f"**Topping:** {topping_str}")
                    col2.write(f"**Total Gula:** {entry['sugar']:.1f}g")
        else:
            st.info("Belum ada konsumsi hari ini")

# -------------------------
# PAGE: HASIL ANALISIS
# -------------------------
elif st.session_state.active_page == "analysis":
    st.title("Hasil Analisis Kesehatan Anda")
    
    if not data['user_profile']['name']:
        st.warning("Silakan setup profil terlebih dahulu di menu Home")
        st.stop()
    
    # Cek kelengkapan data
    has_findrisc = data['findrisc']['score'] is not None
    has_coffee = len(data['coffee_history']) > 0
    
    if not has_findrisc and not has_coffee:
        st.warning("Belum ada data yang dapat dianalisis.")
        st.info("**Langkah selanjutnya:**")
        st.markdown("1. Isi Tes FINDRISC untuk evaluasi risiko diabetes")
        st.markdown("2. Catat konsumsi kopi di Konsumsi Kopi")
        st.stop()
    
    if not has_findrisc:
        st.warning("Anda belum mengisi Tes FINDRISC. Analisis terbatas pada konsumsi kopi.")
    
    if not has_coffee:
        st.warning("Anda belum mencatat konsumsi kopi. Tambahkan data di Konsumsi Kopi.")
    
    st.markdown("---")
    
    # Section 1: Data FINDRISC
    if has_findrisc:
        st.subheader("Profil Risiko Diabetes (FINDRISC)")
        
        col1, col2, col3 = st.columns(3)
        
        score = data['findrisc']['score']
        risk = data['findrisc']['risk_level']
        last_test = datetime.fromisoformat(data['findrisc']['last_updated'])
        days_ago = (datetime.now() - last_test).days
        
        col1.metric("Skor FINDRISC", score)
        col2.metric("Tingkat Risiko", risk)
        col3.metric("Terakhir Diisi", f"{days_ago} hari lalu")
        
        if score < 7:
            st.success("**Risiko Rendah** - Pertahankan gaya hidup sehat!")
        elif score < 12:
            st.info("**Risiko Sedikit Meningkat** - Perhatikan pola makan")
        elif score < 15:
            st.warning("**Risiko Sedang** - Konsultasi dengan dokter")
        elif score < 20:
            st.warning("**Risiko Tinggi** - Pemeriksaan gula darah disarankan")
        else:
            st.error("**Risiko Sangat Tinggi** - Segera konsultasi dokter")
    
    st.markdown("---")
    
    # Section 2: Konsumsi Kopi
    if has_coffee:
        st.subheader("Analisis Konsumsi Gula dari Kopi")
        
        today_sugar = calculate_daily_sugar()
        weekly_avg = calculate_weekly_average()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Gula Hari Ini", f"{today_sugar:.1f}g")
        col2.metric("Batas WHO", "50g/hari")
        col3.metric("Sisa Kuota", f"{max(0, 50-today_sugar):.1f}g")
        col4.metric("Rata-rata 7 Hari", f"{weekly_avg:.1f}g/hari")
        
        # Visualisasi Pie Chart
        st.markdown("#### Visualisasi Kuota Harian")
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        if today_sugar > 0:
            if today_sugar > 50:
                sizes = [50, today_sugar - 50]
                labels = [f'Batas Aman (50g)', f'Kelebihan ({today_sugar - 50:.1f}g)']
                colors = ['#ff6b6b', '#ee5a6f']
                explode = (0, 0.1)
            else:
                sisa = 50 - today_sugar
                sizes = [today_sugar, sisa]
                labels = [f'Terpakai ({today_sugar:.1f}g)', f'Sisa ({sisa:.1f}g)']
                colors = ['#ffd93d', '#6bcf7f']
                explode = (0.05, 0)
            
            wedges, texts, autotexts = ax.pie(
                sizes, 
                labels=labels, 
                autopct='%1.1f%%',
                startangle=90, 
                colors=colors,
                explode=explode,
                textprops={'fontsize': 12, 'weight': 'bold'}
            )
            
            for autotext in autotexts:
                autotext.set_color('white')
        else:
            sizes = [100]
            labels = ['Belum ada konsumsi (0g)']
            colors = ['#e0e0e0']
            ax.pie(sizes, labels=labels, colors=colors, startangle=90)
        
        ax.axis('equal')
        st.pyplot(fig)
        
        if today_sugar > 50:
            st.error(f"**PERINGATAN!** Anda telah mengonsumsi **{today_sugar:.1f}g** gula, "
                    f"**{today_sugar - 50:.1f}g** melebihi batas aman WHO.")
        elif today_sugar > 40:
            st.warning(f"Anda telah menggunakan **{(today_sugar/50)*100:.1f}%** dari kuota harian.")
        elif today_sugar > 0:
            st.success(f"Konsumsi gula masih aman (**{(today_sugar/50)*100:.1f}%** dari kuota).")
    
    st.markdown("---")
    
    # Section 3: Riwayat Konsumsi
    if has_coffee:
        st.subheader("Riwayat Konsumsi")
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            period = st.selectbox(
                "Periode:",
                ["7 Hari Terakhir", "30 Hari Terakhir", "Semua Waktu"]
            )
        
        with col2:
            sort_order = st.selectbox(
                "Urutan:",
                ["Terbaru", "Terlama", "Gula Tertinggi"]
            )
        
        # Filter data
        filtered_history = data['coffee_history'].copy()
        
        if period == "7 Hari Terakhir":
            cutoff = datetime.now() - timedelta(days=7)
            filtered_history = [e for e in filtered_history if datetime.fromisoformat(e['date']) > cutoff]
        elif period == "30 Hari Terakhir":
            cutoff = datetime.now() - timedelta(days=30)
            filtered_history = [e for e in filtered_history if datetime.fromisoformat(e['date']) > cutoff]
        
        # Sort
        if sort_order == "Terbaru":
            filtered_history.sort(key=lambda x: x['date'], reverse=True)
        elif sort_order == "Terlama":
            filtered_history.sort(key=lambda x: x['date'])
        elif sort_order == "Gula Tertinggi":
            filtered_history.sort(key=lambda x: x['sugar'], reverse=True)
        
        # Statistics
        if filtered_history:
            total_entries = len(filtered_history)
            total_sugar = sum(e['sugar'] for e in filtered_history)
            unique_days = len(set(e['date'].split('T')[0] for e in filtered_history))
            avg_per_day = total_sugar / unique_days if unique_days > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Entri", total_entries)
            col2.metric("Total Gula", f"{total_sugar:.1f}g")
            col3.metric("Rata-rata/Hari", f"{avg_per_day:.1f}g")
            col4.metric("Hari Aktif", unique_days)
            
            days_over_limit = sum(1 for day in set(e['date'].split('T')[0] for e in filtered_history)
                                if sum(e['sugar'] for e in filtered_history if e['date'].startswith(day)) > 50)
            
            if days_over_limit > 0:
                st.warning(f"**{days_over_limit} hari** melebihi batas aman dalam periode ini")
        
        st.markdown("---")
        
        # Display grouped entries
        if filtered_history:
            grouped = {}
            for entry in filtered_history:
                day = entry['date'].split('T')[0]
                if day not in grouped:
                    grouped[day] = []
                grouped[day].append(entry)
            
            for day in sorted(grouped.keys(), reverse=(sort_order=="Terbaru")):
                day_entries = grouped[day]
                day_total = sum(e['sugar'] for e in day_entries)
                
                date_obj = datetime.fromisoformat(day)
                day_name = date_obj.strftime("%A, %d %B %Y")
                
                if day_total > 50:
                    status = "Melebihi Batas"
                elif day_total > 40:
                    status = "Mendekati Batas"
                else:
                    status = "Aman"
                
                with st.expander(f"**{day_name}** • {len(day_entries)} entri • {day_total:.1f}g • {status}"):
                    for i, entry in enumerate(day_entries, 1):
                        time_str = datetime.fromisoformat(entry['date']).strftime("%H:%M")
                        topping_str = ", ".join([t.split("(")[0].strip() for t in entry['topping']]) if entry['topping'] else "Tidak ada"
                        
                        st.markdown(f"""
                        **#{i} • {time_str}**
                        - **Minuman:** {entry['drink']}
                        - **Ukuran:** {entry['volume']} × {entry['quantity']} gelas
                        - **Topping:** {topping_str}
                        - **Gula:** {entry['sugar']:.1f}g
                        """)
                        
                        if i < len(day_entries):
                            st.markdown("---")
        else:
            st.info("Tidak ada data untuk periode yang dipilih")
    
    st.markdown("---")
    
    # Section 4: AI Analysis
    if model and (has_findrisc or has_coffee):
        st.subheader("Rekomendasi Personal dari AI")
        
        with st.spinner("AI sedang menganalisis data Anda..."):
            prompt = f"""
Anda adalah GluCoffee AI Assistant, ahli nutrisi dan diabetes educator.

PROFIL PENGGUNA: {data['user_profile']['name']}

DATA KESEHATAN:
"""
            
            if has_findrisc:
                prompt += f"""
- Skor FINDRISC: {data['findrisc']['score']} poin
- Tingkat Risiko: {data['findrisc']['risk_level']}
- Usia: {data['findrisc']['raw_answers'].get('usia', 'N/A')}
- BMI: {data['findrisc']['raw_answers'].get('bmi', 'N/A')}
"""
            
            if has_coffee:
                prompt += f"""
- Konsumsi Gula Hari Ini: {today_sugar:.1f} gram
- Rata-rata Mingguan: {weekly_avg:.1f} gram/hari
- Sisa Kuota Hari Ini: {max(0, 50-today_sugar):.1f} gram
"""
            
            prompt += """

TUGAS:
1. Sapaan hangat dengan nama
2. Analisis hubungan FINDRISC dengan pola konsumsi gula
3. Rekomendasi meal plan hari ini berdasarkan sisa kuota
4. Tips memilih kopi lebih sehat
5. Action plan 3 hari ke depan
6. Motivasi penutup

Gunakan bahasa Indonesia, maksimal 500 kata, dengan emoji.
"""
            
            try:
                response = model.generate_content(prompt)
                
                st.markdown("""
                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 20px; border-radius: 15px; color: white; margin: 20px 0;'>
                    <h3 style='color: white; margin-top: 0;'>Pesan dari AI</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(response.text)
                
                st.markdown("---")
                st.caption("**Disclaimer:** Rekomendasi AI bersifat edukatif, bukan pengganti konsultasi medis.")
                
            except Exception as e:
                st.error(f"Terjadi kesalahan saat menghubungi AI: {str(e)}")
                st.info("Pastikan API key valid. Coba gunakan model 'gemini-pro' jika 'gemini-2.0-flash-exp' tidak tersedia.")
    
    elif not model:
        st.error("Model AI tidak dapat dimuat. Periksa API key Anda.")
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("Langkah Selanjutnya")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Catat Kopi Lagi", use_container_width=True):
            st.session_state.active_page = "coffee"
            st.rerun()
    
    with col2:
        if st.button("Update FINDRISC", use_container_width=True):
            st.session_state.active_page = "findrisc"
            st.rerun()
    
    with col3:
        if st.button("Kembali ke Home", use_container_width=True):
            st.session_state.active_page = "home"
            st.rerun()

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>GluCoffee</strong> • Kesadaran Diabetes Dimulai dari Secangkir Kopi</p>
    <p style='font-size: 12px;'>
        Data FINDRISC berdasarkan Finnish Diabetes Risk Score • 
        Batas gula mengacu pada rekomendasi WHO (50g/hari) • 
        Konsultasikan dengan profesional kesehatan untuk saran medis
    </p>
</div>
""", unsafe_allow_html=True)
