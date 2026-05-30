import streamlit as st
import gspread
import google.generativeai as genai
import json
import requests
import base64
from PIL import Image

# ==========================================
# KONFIGURASI KUNCI API VIA STREAMLIT SECRETS
# ==========================================
# Memanggil kunci dari brankas rahasia Streamlit Cloud
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
IMGBB_API_KEY = st.secrets["IMGBB_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Koneksi Google Sheets via Secrets (Tidak lagi menggunakan file .json)
credentials = dict(st.secrets["gcp_service_account"])
gc = gspread.service_account_from_dict(credentials)

# Buka Spreadsheet
sh = gc.open("Database Evaluasi KOL - Fashion Show Reapin x Raptify Osto x Playground Studio")
worksheet = sh.sheet1

# Inisialisasi Session State
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None
if "image_url" not in st.session_state:
    st.session_state.image_url = ""

# ==========================================
# FUNGSI AUTO-UPLOAD GAMBAR KE IMGBB
# ==========================================
def upload_to_imgbb(uploaded_file):
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json()["data"]["url"]
    return ""

# ==========================================
# FUNGSI AI EXTRACTOR & ESTIMASI CPM
# ==========================================
def extract_data_from_image(image):
    prompt = """
    Tolong baca screenshot profil sosial media ini. Ekstrak data dan kembalikan HANYA format JSON valid.
    
    ATURAN KETAT:
    1. "niche": Pilih HANYA satu: "Fashion", "Lifestyle", atau "Influencer General".
    2. "skala": 
       - "Makro Influencer" (> 25k followers)
       - "Mikro Influencer" (10k - 25k followers)
       - "Nano Influencer" (5k - 10k followers)
       - "Non Influencer" (< 5k followers)
    3. "estimasi_rate": Hitung menggunakan metode Cost Per Mille (CPM).
       - Ubah followers jadi angka. Asumsikan rata-rata views = 10% dari followers.
       - Batas bawah = (views / 1000) * 50000
       - Batas atas = (views / 1000) * 300000
       - Tuliskan hasilnya sebagai string harga, contoh format: "Rp 50.000 - Rp 300.000"
       
    Struktur JSON:
    {
        "nama_kol": "Nama asli",
        "username": "Username/handle",
        "platform": "Instagram atau TikTok",
        "followers": "Jumlah followers mentah",
        "niche": "Sesuai Aturan 1",
        "skala": "Sesuai Aturan 2",
        "estimasi_rate": "Sesuai Aturan 3"
    }
    """
    
    response = model.generate_content([prompt, image])
    cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned_text)

# ==========================================
# ANTARMUKA STREAMLIT (UI)
# ==========================================
st.set_page_config(page_title="OpenClaw - Reapin KOL Scraper", layout="wide")
st.title("🦅 OpenClaw KOL Extractor")

uploaded_file = st.file_uploader("Pilih Screenshot Profil...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Screenshot Profil', width=400)
    
    if st.button("🚀 Ekstrak dengan AI & Upload Gambar"):
        with st.spinner('Menganalisis gambar dan mengunggah ke server...'):
            try:
                st.session_state.extracted_data = extract_data_from_image(image)
                st.session_state.image_url = upload_to_imgbb(uploaded_file)
                st.success("Selesai! Silakan review data di bawah.")
            except Exception as e:
                st.error(f"Gagal memproses: {e}")

# ==========================================
# FASE REVIEW & PENGIRIMAN DATA
# ==========================================
if st.session_state.extracted_data:
    st.divider()
    data = st.session_state.extracted_data
    
    with st.form("form_review"):
        col1, col2 = st.columns(2)
        
        with col1:
            in_ssan = st.text_input("1. Ssan Sosmed (URL Auto-Generated)", st.session_state.image_url)
            in_nama = st.text_input("2. Nama KOL", data.get("nama_kol", ""))
            in_username = st.text_input("3. Username / Handle", data.get("username", ""))
            
            plat_opts = ["Instagram", "TikTok", "Lainnya"]
            plat_def = data.get("platform", "Instagram") if data.get("platform") in plat_opts else "Instagram"
            in_platform = st.selectbox("4. Platform Utama", plat_opts, index=plat_opts.index(plat_def))
            
            in_link1 = st.text_input("5. Link Profil", f"https://www.{in_platform.lower()}.com/{in_username.replace('@', '')}")
            in_link2 = st.text_input("6. Link Profil 2 (Opsional)", "")
            
            niche_opts = ["Fashion", "Lifestyle", "Influencer General"]
            niche_def = data.get("niche", "Fashion") if data.get("niche") in niche_opts else "Fashion"
            in_niche = st.selectbox("7. Kategori / Niche", niche_opts, index=niche_opts.index(niche_def))
            
            skala_opts = ["Makro Influencer", "Mikro Influencer", "Nano Influencer", "Non Influencer"]
            skala_def = data.get("skala", "Non Influencer") if data.get("skala") in skala_opts else "Non Influencer"
            in_skala = st.selectbox("8. Skala Influencer", skala_opts, index=skala_opts.index(skala_def))

        with col2:
            in_followers = st.text_input("9. Jumlah Followers", data.get("followers", ""))
            in_kualitas = st.selectbox("10. Kualitas Konten (1-5)", ["", "1", "2", "3", "4", "5"])
            in_gaya = st.text_input("11. Kecocokan Gaya", "")
            in_brand = st.text_input("12. Kecocokan Brand", "")
            in_rate = st.text_input("13. Estimasi Rate Card (Rp)", data.get("estimasi_rate", ""))
            in_kontak = st.text_input("14. Kontak (Email/WA)", "")
            in_status = st.selectbox("15. Status Undangan", ["Belum Diundang", "Menerima", "Menolak"], index=0)
            in_catatan = st.text_area("16. Catatan Tambahan", "")
            
        submitted = st.form_submit_button("💾 Simpan ke Google Sheets")
        
        if submitted:
            with st.spinner("Mencari baris kosong dan menyimpan data..."):
                try:
                    formula_gambar = f'=IMAGE("{in_ssan}")' if in_ssan else ""
                    
                    row_data = [
                        "", formula_gambar, in_nama, in_username, in_platform,
                        in_link1, in_link2, in_niche, in_skala, in_followers,
                        in_kualitas, in_gaya, in_brand, in_rate, in_kontak,
                        in_status, in_catatan
                    ]
                    
                    kolom_nama = worksheet.col_values(3)
                    baris_baru = len(kolom_nama) + 1
                    
                    worksheet.update(values=[row_data], range_name=f"A{baris_baru}", value_input_option='USER_ENTERED')
                    
                    st.success(f"✅ Data berhasil masuk ke baris ke-{baris_baru} di Google Sheets!")
                    st.session_state.extracted_data = None
                    st.session_state.image_url = ""
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat menyimpan ke Sheets: {e}")