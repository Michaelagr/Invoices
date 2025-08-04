import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="Bank-Transaktionen Organizer", layout="wide")

KATEGORIEN = [
    "Lebensmittel", "Miete", "Transport", "Freizeit", "Rechnungen", "Sonstiges"
]

def parse_postbank_txt(file):
    """Parst den hochgeladenen Postbank-Umsatzbericht."""
    text = file.read().decode('utf-8')
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    transactions = []
    idx = 0
    while idx < len(lines) - 4:
        # Suche nach Zeilen, die wie ein Datum aussehen (Tagesformat, z.B. 26.08.2024)
        if re.match(r"\d{2}\.\d{2}\.\d{4}", lines[idx]):
            datum = lines[idx]
            betrag_line = lines[idx + 1]
            betrag = float(betrag_line.replace('.', '').replace(',', '.').replace(' EUR', '').replace('€', ''))
            
            empfaenger = lines[idx + 2]
            verwendungszweck = lines[idx + 3]
            art = lines[idx + 4]
            
            transactions.append({
                "Datum": datum,
                "Betrag": betrag,
                "Empfänger": empfaenger,
                "Verwendungszweck": verwendungszweck,
                "Art": art,
                "Kategorie": "",
            })
            idx += 5
        else:
            idx += 1
    return pd.DataFrame(transactions)

# --- Streamlit UI ---

st.title("💳 Bank-Transaktionen Organizer")
st.markdown("""
Organisiere deine Postbank-Umsätze: Kategorisiere Transaktionen, analysiere Ausgaben pro Kategorie und lade Daten als TXT herunter.
""")

uploaded_file = st.file_uploader("Lade deine Postbank-TXT-Datei hoch", type=["txt"])

if uploaded_file:
    df = parse_postbank_txt(uploaded_file)
    if "df" not in st.session_state or st.session_state["df"].empty:
        st.session_state["df"] = df
    else:
        # Wenn schon kategorisiert, nutze den Session-State
        df = st.session_state["df"]

    st.header("🔎 Transaktionen kategorisieren")
    st.markdown("Wähle eine Kategorie und (optional) ähnliche Transaktionen.")

    for idx, row in df.iterrows():
        kategorie = row["Kategorie"]
        with st.expander(
            f"{row['Datum']} | {row['Empfänger']} | {row['Betrag']:,.2f}€ | {row['Verwendungszweck']}",
            expanded=False
        ):
            selected_kat = st.selectbox(
                "Kategorie auswählen:",
                options=[""] + KATEGORIEN,
                index=(KATEGORIEN.index(kategorie) + 1) if kategorie else 0,
                key=f"cat_{idx}"
            )

            # Ähnliche Transaktionen suchen
            if selected_kat:
                similar = df[
                    (df["Empfänger"] == row["Empfänger"])
                    & (df.index != idx)
                    & (df["Kategorie"] == "")
                ]
                if not similar.empty:
                    st.markdown("**Ähnliche, noch nicht kategorisierte Transaktionen:**")
                    for sim_idx, sim_row in similar.iterrows():
                        add = st.checkbox(
                            f"{sim_row['Datum']} | {sim_row['Betrag']:,.2f}€ | {sim_row['Verwendungszweck']}",
                            key=f"sim_{idx}_{sim_idx}"
                        )
                        if add:
                            df.at[sim_idx, "Kategorie"] = selected_kat
            # Speichern
            df.at[idx, "Kategorie"] = selected_kat

    st.session_state["df"] = df

    # --- Analyse ---
    st.header("📊 Auswertung nach Kategorie")
    df_kat = df[df["Kategorie"] != ""]
    if not df_kat.empty:
        st.markdown("### Übersicht")
        summary = df_kat.groupby("Kategorie")["Betrag"].sum().reset_index()
        st.bar_chart(summary, x="Kategorie", y="Betrag")

        st.markdown("### Export")
        kategorie_select = st.selectbox("Kategorie für Export wählen:", options=KATEGORIEN)
        download_df = df_kat[df_kat["Kategorie"] == kategorie_select]
        if not download_df.empty:
            txt = download_df.to_csv(
                sep='\t', index=False, columns=["Datum", "Betrag", "Empfänger", "Verwendungszweck", "Art", "Kategorie"]
            )
            st.download_button(
                label=f"{kategorie_select} als TXT herunterladen",
                data=txt,
                file_name=f"{kategorie_select}.txt"
            )
    else:
        st.info("Noch keine kategorisierten Transaktionen.")

    st.markdown("""
    <style>
    .stSelectbox, .stCheckbox, .stExpander, .stButton, .stDownloadButton {font-size: 1.1em;}
    .stMarkdown {font-size: 1.1em;}
    </style>
    """, unsafe_allow_html=True)

else:
    st.info("Bitte lade zuerst eine TXT-Datei hoch.")
