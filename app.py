import streamlit as st
import pandas as pd
import io
import re

# --- 1. KONFIGURACE ---
st.set_page_config(page_title="Splitter Obalů Final", page_icon="✂️", layout="wide")

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

# KLT a Drobné
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

# Palety a Velké boxy (včetně CARTON 16, 17, 18)
PALLET_CODES = [
    '8216.00LP.04', '8216.00KP.04', '8216.2032.01', '8216.5009.01',
    '8216.1875.05', '8216.0010.03', '9860000415900', '8216.5010.01',
    '8216.2035.01', '8216.1874.05', '8216.5003.01', '9860000416100',
    '9860000415300', '9860000876100', '9860001205300',
    'CARTON-16', 'CARTON-17', 'CARTON-18'
]

# --- 3. LOGIKA TŘÍDĚNÍ ---
def split_packaging_final(text):
    if not isinstance(text, str) or not text.strip():
        return "", "", "", ""
    
    items = [x.strip() for x in text.split(';') if x.strip()]
    
    klt_list = []
    pallet_list = []
    carton_list = []
    other_list = []
    
    for item in items:
        # Získání čistého kódu
        code_match = re.match(r"^([^\s(]+)", item)
        if not code_match:
            other_list.append(item)
            continue
            
        code = code_match.group(1).strip()
        
        # 1. KROK: KLT
        if code in KLT_CODES:
            klt_list.append(item)
            continue
            
        # 2. KROK: Palety (vč. Carton 16-18)
        if code in PALLET_CODES:
            pallet_list.append(item)
            continue
            
        # 3. KROK: Malé Kartony (0-15)
        if "CARTON" in code.upper():
            # Zkusíme najít číslo (např. CARTON-05 -> 5)
            num_match = re.search(r"[-_]?(\d+)", code)
            if num_match:
                try:
                    num = int(num_match.group(1))
                    if 0 <= num <= 15:
                        carton_list.append(item)
                        continue
                except ValueError:
                    pass
            
            # Pokud je to CARTON, ale není v Paletách a není 0-15 -> Ostatní
            other_list.append(item)
            continue
            
        # 4. KROK: Vše ostatní
        other_list.append(item)
        
    return "; ".join(klt_list), "; ".join(pallet_list), "; ".join(carton_list), "; ".join(other_list)

# --- 4. UI APLIKACE ---
st.title("✂️ Splitter Obalů (4 sloupce)")
st.markdown("Rozdělí data na: **KLT** | **Palety** | **Cartons (0-15)** | **Ostatní**")

uploaded_file = st.file_uploader("Nahrajte soubor rozdělit.xlsx", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None)
        else:
            df = pd.read_excel(uploaded_file, header=None)
        
        # Očekáváme strukturu: Sloupec A = Zakázka, Sloupec B = Text obalů
        # Přejmenujeme pro jistotu
        df.columns = ['Zakázka', 'Obaly_Zdroj'] + list(df.columns[2:])
        
        # Aplikace logiky
        split_result = df['Obaly_Zdroj'].apply(lambda x: pd.Series(split_packaging_final(x)))
        split_result.columns = ['KLT', 'Palety', 'Cartons', 'Ostatní']
        
        # Spojení
        final_df = pd.concat([df['Zakázka'], split_result], axis=1)
        
        st.success("✅ Rozdělení proběhlo úspěšně!")
        st.dataframe(final_df.head(50), use_container_width=True)
        
        # Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name="Split_Data")
            ws = writer.sheets['Split_Data']
            ws.set_column(0, 0, 15)  # Zakázka
            ws.set_column(1, 1, 40)  # KLT
            ws.set_column(2, 2, 40)  # Palety
            ws.set_column(3, 3, 30)  # Cartons
            ws.set_column(4, 4, 30)  # Ostatní
            
        st.download_button(
            label="📥 STÁHNOUT VÝSLEDEK (XLSX)",
            data=buffer.getvalue(),
            file_name="rozděleno_4sloupce.xlsx",
            mime="application/vnd.ms-excel"
        )

    except Exception as e:
        st.error(f"Chyba při zpracování: {e}")
