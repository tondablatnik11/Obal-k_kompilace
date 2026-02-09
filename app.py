import streamlit as st
import pandas as pd
import io

# --- 1. KONFIGURACE ---
st.set_page_config(page_title="HU Order Matcher Pro", layout="wide")

# Seznamy pro rozřazování (vychází z tvých pravidel) 
PALLET_WHITELIST = ['8216.00LP.04', '8216.00KP.04', '8216.2032.01', '8216.5009.01', '8216.1875.05', '8216.0010.03', '9860000415900', 'CARTON-16', 'CARTON-17', 'CARTON-18']
KLT_WHITELIST = ['8216.3215.01', '8216.4129.01', '8216.4314.01', '8216.4329.01', '8216.6129.01', '9860000422000', '9860000421400', '000198390A000']

st.title("📋 HU Order Matcher - Rozdělení obalů")

with st.sidebar:
    file_xlsx = st.file_uploader("1. Nahrát Pack.xlsx", type=['xlsx', 'csv'])
    file_txt = st.file_uploader("2. Nahrát Seznam zakázek (txt)", type=['txt'])

if file_xlsx and file_txt:
    try:
        df_pack = pd.read_csv(file_xlsx) if file_xlsx.name.endswith('.csv') else pd.read_excel(file_xlsx)
        
        txt_content = file_txt.read().decode("utf-8")
        order_list = [line.strip() for line in txt_content.splitlines() if line.strip()]
        df_orders = pd.DataFrame({'Zakázka': order_list})
        df_orders['Zakázka'] = df_orders['Zakázka'].astype(str)

        col_deliv = 'Generated delivery'
        col_pack = 'Packaging materials'

        if col_deliv in df_pack.columns and col_pack in df_pack.columns:
            df_pack[col_deliv] = df_pack[col_deliv].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # Funkce pro rozdělení skupin
            def get_grouped_hu(group, whitelist):
                counts = group[group[col_pack].isin(whitelist)][col_pack].value_counts()
                return "; ".join([f"{str(code)} ({count}x)" for code, count in counts.items()])

            # Vytvoření souhrnů zvlášť pro KLT a Palety 
            klt_summary = df_pack.groupby(col_deliv).apply(lambda x: get_grouped_hu(x, KLT_WHITELIST)).reset_index(name='KLT')
            pal_summary = df_pack.groupby(col_deliv).apply(lambda x: get_grouped_hu(x, PALLET_WHITELIST)).reset_index(name='Palety')

            # Spojení do finální tabulky (zachování pořadí z TXT) [cite: 2]
            output_df = pd.merge(df_orders, klt_summary, on='Zakázka', how='left')
            output_df = pd.merge(output_df, pal_summary, on='Zakázka', how='left').fillna("")

            st.dataframe(output_df, use_container_width=True, hide_index=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                output_df.to_excel(writer, index=False, sheet_name="Rozdělené_Obaly")
                ws = writer.sheets['Rozdělené_Obaly']
                ws.set_column(0, 0, 15)
                ws.set_column(1, 2, 45)

            st.download_button("📥 Stáhnout rozdělený Excel", buffer.getvalue(), "rozdělené_obaly.xlsx")
    except Exception as e:
        st.error(f"Chyba: {e}")
