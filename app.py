import streamlit as st
import pandas as pd
import io

# --- 1. KONFIGURACE A DARK THEME ---
st.set_page_config(
    page_title="HU Order Matcher Pro",
    page_icon="📋",
    layout="wide"
)

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    h1 { color: #58a6ff !important; font-family: 'Inter', sans-serif; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    .stButton>button { background-color: #238636; color: white; border-radius: 6px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 HU Order Matcher Pro")
st.markdown("Párování zakázek do sloupců se zachováním pořadí z TXT.")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.subheader("Vstupní soubory")
    file_xlsx = st.file_uploader("1. Nahrát Pack.xlsx", type=['xlsx', 'csv'])
    file_txt = st.file_uploader("2. Nahrát Seznam zakázek (txt)", type=['txt'])
    st.markdown("---")
    st.caption("Verze 1.1 | Sloupcový export")

# --- 3. LOGIKA ---
if file_xlsx and file_txt:
    try:
        # Načtení dat o balení
        if file_xlsx.name.endswith('.csv'):
            df_pack = pd.read_csv(file_xlsx)
        else:
            df_pack = pd.read_excel(file_xlsx)

        # Načtení TXT seznamu (klíč pro pořadí)
        txt_content = file_txt.read().decode("utf-8")
        order_list = [line.strip() for line in txt_content.splitlines() if line.strip()]
        df_orders = pd.DataFrame({'Zakázka': order_list})
        df_orders['Zakázka'] = df_orders['Zakázka'].astype(str)

        # Identifikace sloupců v Pack.xlsx
        # Použijeme tvé názvy: 'Generated delivery' a 'Packaging materials'
        col_deliv = 'Generated delivery'
        col_pack = 'Packaging materials'

        if col_deliv in df_pack.columns and col_pack in df_pack.columns:
            # Čištění ID zakázek v Excelu
            df_pack[col_deliv] = df_pack[col_deliv].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # Seskupení obalů do jednoho řádku pro každou zakázku
            def group_hu(group):
                counts = group[col_pack].value_counts()
                return "; ".join([f"{str(code)} ({count}x)" for code, count in counts.items()])

            pack_summary = df_pack.groupby(col_deliv).apply(group_hu).reset_index()
            pack_summary.columns = ['Zakázka', 'Obalový materiál']

            # Spojení (Merge) - zachová pořadí z df_orders (z TXT)
            output_df = pd.merge(df_orders, pack_summary, on='Zakázka', how='left')
            output_df['Obalový materiál'] = output_df['Obalový materiál'].fillna("Nenalezeno")

            # --- 4. ZOBRAZENÍ A EXPORT ---
            st.subheader("Výsledná tabulka")
            st.dataframe(output_df, use_container_width=True, hide_index=True)

            # Příprava Excelu ke stažení
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                output_df.to_excel(writer, index=False, sheet_name="Matched_Orders")
                # Úprava šířky sloupců v Excelu
                worksheet = writer.sheets['Matched_Orders']
                worksheet.set_column(0, 0, 20) # Sloupec Zakázka
                worksheet.set_column(1, 1, 60) # Sloupec Obaly

            st.download_button(
                label="📥 STÁHNOUT VÝSLEDEK (XLSX)",
                data=buffer.getvalue(),
                file_name="sparovane_zakazky.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.error(f"V souboru Pack.xlsx nebyly nalezeny sloupce '{col_deliv}' nebo '{col_pack}'.")

    except Exception as e:
        st.error(f"Chyba: {e}")
else:
    st.info("Nahrajte Pack.xlsx a TXT seznam zakázek pro vygenerování tabulky.")
