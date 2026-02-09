import streamlit as st
import pandas as pd
import io
import re

# --- 1. KONFIGURACE ---
st.set_page_config(page_title="Splitter Obalů Pro", page_icon="✂️", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    h1 { color: #58a6ff !important; font-family: 'Inter', sans-serif; }
    .stButton>button { background-color: #238636; color: white; border-radius: 6px; width: 100%; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KOMPLETNÍ DATABÁZE (Z app.py + Pack.xlsx) ---

# A) KLT a Drobné obaly (včetně Vík a Prokladů)
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
    '9860000423300', '8216.9040.01'
]

# B) Palety a Velké nosiče
PALLET_CODES = [
    '8216.00LP.04', '8216.00KP.04', '8216.2032.01', '8216.5009.01',
    '8216.1875.05', '8216.0010.03', '9860000415900', '8216.5010.01',
    '8216.2035.01', '8216.1874.05', '8216.5003.01', '9860000416100',
    '9860000415300', '9860000876100', '9860001205300',
    'CARTON-16', 'CARTON-17', 'CARTON-18'
]

# --- 3. LOGIKA ROZDĚLENÍ ---
def split_packaging(text):
    if not isinstance(text, str) or not text.strip():
        return "", ""
    
    items = [x.strip() for x in text.split(';') if x.strip()]
    
    klt_list = []
    pallet_list = []
    
    for item in items:
        # Získání čistého kódu (vše před mezerou nebo závorkou)
        code_match = re.match(r"^([^\s(]+)", item)
        if code_match:
            code = code_match.group(1).strip()
            
            # 1. KLT Whitelist
            if code in KLT_CODES:
                klt_list.append(item)
            # 2. Pallet Whitelist
            elif code in PALLET_CODES:
                pallet_list.append(item)
            # 3. Dynamická pravidla (CARTON)
            elif "CARTON" in code:
                # Menší kartony obvykle do KLT/Box, větší do Palet?
                # Zde dáváme vše co není C-16/17/18 do Palet (default) nebo KLT?
                # Dle tvého vzoru v app.py byly CARTON-09, 05 atd. brány jako "krabice" -> KLT sloupec?
                # Pokud chceš CARTON-02, 05 atd. v KLT sloupci, odkomentuj řádek níže:
                # klt_list.append(item) 
                pallet_list.append(item) # Defaultně necháváme v Paletách/Ostatní
            else:
                # Neznámý kód -> Bezpečně do Palet (aby byl vidět)
                pallet_list.append(item) 
                
    return "; ".join(klt_list), "; ".join(pallet_list)

# --- 4. UI APLIKACE ---
st.title("✂️ Splitter Obalů Pro (v1.2)")
st.markdown("Rozdělí obaly na **KLT** (včetně vík a EPP) a **Palety** (včetně Gitterboxů).")

uploaded_file = st.file_uploader("Nahrajte soubor rozdělit.xlsx", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # Načtení
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None)
        else:
            df = pd.read_excel(uploaded_file, header=None)
        
        # Přejmenování (Předpoklad: Sloupec A=Zakázka, B=Obaly)
        # Pokud má soubor hlavičku, df.iloc[0] by to odhalilo, zde bereme natvrdo data
        df.columns = ['Zakázka', 'Obaly_Full'] + list(df.columns[2:])
        
        # Aplikace logiky
        split_result = df['Obaly_Full'].apply(lambda x: pd.Series(split_packaging(x)))
        split_result.columns = ['KLT', 'Palety']
        
        # Sestavení výsledku
        final_df = pd.concat([df['Zakázka'], split_result], axis=1)
        
        st.success("✅ Hotovo! Níže je náhled:")
        st.dataframe(final_df.head(20), use_container_width=True)
        
        # Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name="Split_Data")
            ws = writer.sheets['Split_Data']
            ws.set_column(0, 0, 15) # Zakázka
            ws.set_column(1, 1, 60) # KLT
            ws.set_column(2, 2, 60) # Palety
            
        st.download_button(
            label="📥 Stáhnout rozdělený XLSX",
            data=buffer.getvalue(),
            file_name="rozdělené_obaly_v1.2.xlsx",
            mime="application/vnd.ms-excel"
        )

    except Exception as e:
        st.error(f"Chyba při zpracování: {e}")
