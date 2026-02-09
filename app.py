import streamlit as st
import pandas as pd
import io

# --- 1. KONFIGURACE ---
st.set_page_config(
    page_title="HU Order Matcher",
    page_icon="📋",
    layout="wide"
)

# Dark Mode a čistý design
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    h1 { color: #58a6ff !important; }
    .stDataFrame { border: 1px solid #30363d; }
    .stButton>button { background-color: #238636; color: white; border-radius: 6px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 HU Order Matcher")
st.markdown("Párování zakázek z TXT seznamu s daty o obalech z Pack.xlsx.")

# --- 2. SIDEBAR / INPUTY ---
with st.sidebar:
    st.subheader("Vstupní data")
    file_xlsx = st.file_uploader("Nahrát Pack.xlsx", type=['xlsx', 'csv'])
    file_txt = st.file_uploader("Nahrát Seznam zakázek (txt)", type=['txt'])
    st.caption("Verze 1.0 | Dark Mode")

# --- 3. LOGIKA ZPRACOVÁNÍ ---
if file_xlsx and file_txt:
    try:
        # Načtení Pack.xlsx
        if file_xlsx.name.endswith('.csv'):
            df_pack = pd.read_csv(file_xlsx)
        else:
            df_pack = pd.read_excel(file_xlsx)

        # Načtení TXT seznamu zakázek (zachování pořadí)
        txt_content = file_txt.read().decode("utf-8")
        order_list = [line.strip() for line in txt_content.splitlines() if line.strip()]
        
        # Příprava DF pro pořadí
        df_orders = pd.DataFrame({'Zakázka': order_list})
        df_orders['Zakázka'] = df_orders['Zakázka'].astype(str)

        # Vyčištění Pack dat (sloupce 'Generated delivery' a 'Packaging materials')
        # Poznámka: Sloupce se v různých exportech mohou jmenovat jinak, 
        # zde předpokládám standardní názvy z tvého souboru.
        col_deliv = 'Generated delivery'
        col_pack = 'Packaging materials'
        
        df_pack[col_deliv] = df_pack[col_deliv].astype(str).str.replace(r'\.0$', '', regex=True)
        
        # Seskupení obalů podle zakázky
        def summarize_packaging(group):
            counts = group[col_pack].value_counts()
            parts = [f"{str(code)} ({count}x)" for code, count in counts.items()]
            return " - " + "; ".join(parts)

        # Vytvoření mapovací tabulky
        packaging_summary = df_pack.groupby(col_deliv).apply(summarize_packaging).reset_index()
        packaging_summary.columns = ['Zakázka', 'Packaging Details']

        # Spojení se seznamem zakázek (Left Join pro zachování pořadí z TXT)
        final_result = pd.merge(df_orders, packaging_summary, on='Zakázka', how='left')
        final_result['Packaging Details'] = final_result['Packaging Details'].fillna(" - Nenalezeno")
        
        # Vytvoření finálního textového řetězce
        final_result['Full String'] = final_result['Zakázka'] + final_result['Packaging Details']

        # --- 4. ZOBRAZENÍ VÝSLEDKŮ ---
        st.subheader("Výsledek (seřazeno dle TXT)")
        
        # Zobrazení ve formátu, který jsi chtěl
        result_text = "\n".join(final_result['Full String'].tolist())
        st.text_area("Náhled (lze kopírovat):", value=result_text, height=400)

        # Export do TXT
        st.download_button(
            label="📥 Stáhnout výsledek jako TXT",
            data=result_text,
            file_name="matched_orders.txt",
            mime="text/plain"
        )

    except Exception as e:
        st.error(f"Chyba při zpracování: {e}")
        st.info("Ujistěte se, že Pack.xlsx obsahuje sloupce 'Generated delivery' a 'Packaging materials'.")
else:
    st.info("Prosím nahrajte oba soubory pro spuštění párování.")
