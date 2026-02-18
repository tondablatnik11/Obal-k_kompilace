import streamlit as st
import pandas as pd
import io
import re

# --- 1. KONFIGURACE ---
st.set_page_config(page_title="Splitter Obalů v1.6 (Report)", page_icon="✂️", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    h1 { color: #58a6ff !important; font-family: 'Inter', sans-serif; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    .stButton>button { background-color: #238636; color: white; border-radius: 6px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABÁZE KÓDŮ ---

# A) KLT a Drobné
KLT_CODES = [
    '8216.3215.01', '8216.4129.01', '8216.4314.01', '8216.4329.01', 
    '8216.6129.01', '9860000422000', '9860000421400', '000198390A000',
    '8216.0100.10', '8216.0505.05', '8216.4328.01', '9860001178000',
    '8216.0780.04', '8216.6428.01', '8216.00LR.04', '8216.00LD.04',
    '9860001393000', '9860000417900', '9860000419300', '9800004218000',
    '8216.0003.10', '8216.0092.04', '8216.0782.04', '8216.0783.04',
    '8216.0750.04', '9860000126500', '9860001175000', '9860001195800',
    '8216.9041.01', '9860001530500', '8216.9094.01', '9860001530600',
    '8216.9093.01', '8216.0474.05', '9860001254000', '8216.6429.01',
    '9860000423300', '8216.9040.01', '8216.6421.06', '8216.4329.03'
]

# B) Palety a Velké boxy
PALLET_CODES = [
    '8216.00LP.04', '8216.00KP.04', '8216.2032.01', '8216.5009.01',
    '8216.1875.05', '8216.0010.03', '9860000415900', '8216.5010.01',
    '8216.2035.01', '8216.1874.05', '8216.5003.01', '9860000416100',
    '9860000415300', '9860000876100', '9860001205300', '8216.0036.03',
    'CARTON-16', 'CARTON-17', 'CARTON-18'
]

# C) Speciální Kartony
SPECIFIC_CARTONS = ['9800775063000', '9800775061000']

# --- 3. POMOCNÉ FUNKCE ---

def get_description(code, desc_map):
    """Vrátí kód + popis, pokud existuje."""
    desc = desc_map.get(code, "")
    if desc:
        return f"{code} - {desc}"
    return code

def split_packaging_final(text, desc_map):
    if not isinstance(text, str) or not text.strip():
        return "", "", "", ""
    
    items = [x.strip() for x in text.split(';') if x.strip()]
    
    klt_list = []
    pallet_list = []
    carton_list = []
    other_list = []
    
    for item in items:
        # Získání čistého kódu (vše před mezerou nebo závorkou)
        code_match = re.match(r"^([^\s(]+)", item)
        if not code_match:
            other_list.append(item)
            continue
            
        code = code_match.group(1).strip()
        
        # ZMĚNA: Již NEHLEDÁME ani nepřidáváme počet kusů "(Xx)"
        # Použijeme rovnou čistý kód (případně s popisem)
        full_desc_str = get_description(code, desc_map)

        # 1. KROK: KLT
        if code in KLT_CODES:
            klt_list.append(full_desc_str)
            continue
            
        # 2. KROK: Palety
        if code in PALLET_CODES:
            pallet_list.append(full_desc_str)
            continue

        # 3. KROK: Specifické Kartony
        if code in SPECIFIC_CARTONS:
            carton_list.append(full_desc_str)
            continue
            
        # 4. KROK: Logika CARTON-XX
        if "CARTON" in code.upper():
            num_match = re.search(r"[-_\s]?(\d+)", code)
            if num_match:
                try:
                    num = int(num_match.group(1))
                    if (0 <= num <= 15) or (num == 22):
                        carton_list.append(full_desc_str)
                        continue
                except ValueError:
                    pass
            other_list.append(full_desc_str)
            continue
            
        # 5. KROK: Vše ostatní
        other_list.append(full_desc_str)
        
    return "; ".join(klt_list), "; ".join(pallet_list), "; ".join(carton_list), "; ".join(other_list)

# --- 4. UI APLIKACE ---
st.title("✂️ Splitter Obalů (v1.6 - Logistics Report)")
st.markdown("Vstup: **logistics_report.xlsx** | Výstup: Rozdělení **bez počtů kusů**")

# Sidebar
with st.sidebar:
    st.header("Vstupní data")
    uploaded_file = st.file_uploader("1. logistics_report.xlsx", type=['xlsx', 'csv'])
    st.markdown("---")
    st.header("Databáze popisů (Volitelné)")
    desc_file = st.file_uploader("2. empties_description.xlsx", type=['xlsx', 'csv'])
    st.caption("Pokud nahrajete popisy, obaly budou ve formátu 'Kód - Popis'. Jinak jen 'Kód'.")

# Načtení mapy popisů
description_map = {}
if desc_file:
    try:
        if desc_file.name.endswith('.csv'):
            df_desc = pd.read_csv(desc_file, header=None)
        else:
            df_desc = pd.read_excel(desc_file, header=None)
        description_map = pd.Series(df_desc.iloc[:, 1].values, index=df_desc.iloc[:, 0].astype(str).str.strip()).to_dict()
        st.sidebar.success(f"Načteno {len(description_map)} popisů.")
    except Exception as e:
        st.sidebar.error(f"Chyba popisů: {e}")

# Hlavní logika
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # ZMĚNA: Hledáme specifický sloupec pro Logistics Report
        target_col = 'Packaging Details'
        if target_col not in df.columns:
            st.error(f"Chyba: Soubor neobsahuje sloupec '{target_col}'.")
            st.info("Ujistěte se, že nahráváte 'logistics_report.xlsx' s hlavičkou.")
            st.stop()
        
        # Aplikace logiky
        st.write("Zpracovávám data...")
        split_result = df[target_col].apply(lambda x: pd.Series(split_packaging_final(x, description_map)))
        split_result.columns = ['KLT', 'Pallets', 'Cartons', 'Ostatní']
        
        # Spojení - zachováme původní data a přidáme nové sloupce
        final_df = pd.concat([df, split_result], axis=1)
        
        st.success("✅ Hotovo!")
        st.dataframe(final_df.head(20), use_container_width=True)
        
        # Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name="Split_Data")
            ws = writer.sheets['Split_Data']
            # Nastavení šířky sloupců (odhad)
            for i, col in enumerate(final_df.columns):
                ws.set_column(i, i, 20)
            
        st.download_button(
            label="📥 STÁHNOUT VÝSLEDEK (XLSX)",
            data=buffer.getvalue(),
            file_name="split_logistics_report_v1.6.xlsx",
            mime="application/vnd.ms-excel"
        )

    except Exception as e:
        st.error(f"Chyba při zpracování: {e}")
