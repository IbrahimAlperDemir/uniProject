import pandas as pd
from openai import OpenAI
import streamlit as st
from difflib import SequenceMatcher

# ---------------------------------
# OPENAI CLIENT
# ---------------------------------
client = OpenAI()

# ---------------------------------
# UTILS
# ---------------------------------
def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# ---------------------------------
# 1) EXCEL OKUMA
# ---------------------------------
def read_testcases_from_excel(file):
    return pd.read_excel(file)

# ---------------------------------
# 2) LLM TEST CASE ÜRETİMİ
# ---------------------------------
def generate_llm_testcases(project_name="Akakçe"):
    prompt = f"""
'{project_name}' web sitesi için TOPLAM 15 adet test case üret.

KURALLAR:
- TAM OLARAK 15 SATIR
- SADECE test case satırları
- Başlık yazma
- Her satır '|' ile ayrılmalı

FORMAT:
ID | Title | Test Type | Steps | Expected Result

İÇERİK:
- En az 7 Negatif
- En az 4 Performans
- Kalanlar Pozitif olabilir
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    rows = []
    for line in response.choices[0].message.content.split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 5:
            rows.append(parts)

    return pd.DataFrame(
        rows,
        columns=["ID", "Title", "Test Type", "Steps", "Expected Result"]
    )

# ---------------------------------
# 3) KARŞILAŞTIRMA RAPORU
# ---------------------------------
def compare_testcases(original_df, llm_df):
    results = []
    matched_llm_titles = set()

    # Manuel → LLM eşleşmeleri
    for _, orig in original_df.iterrows():
        best_score = 0
        best_llm_row = None

        for _, llm in llm_df.iterrows():
            score = similarity(orig["Title"], llm["Title"])
            if score > best_score:
                best_score = score
                best_llm_row = llm

        if best_score >= 0.5:
            matched_llm_titles.add(best_llm_row["Title"])
            results.append({
                "Test Case Title": orig["Title"],
                "Durum": "EŞLEŞME VAR",
                "LLM Steps": best_llm_row["Steps"]
            })

    # LLM → Manuel olmayanlar (Yeni Öneriler)
    for _, llm in llm_df.iterrows():
        if llm["Title"] not in matched_llm_titles:
            results.append({
                "Test Case Title": llm["Title"],
                "Durum": "YENİ ÖNERİ",
                "LLM Steps": llm["Steps"]
            })

    return pd.DataFrame(results)

# ---------------------------------
# 4) STREAMLIT UI
# ---------------------------------
def main():
    st.set_page_config(page_title="Akakçe Test Case AI", layout="wide")
    st.title("Akakçe Test Case Karşılaştırma Sistemi")

    uploaded_file = st.file_uploader(
        "Manuel Test Case Excel Yükleyin",
        type=["xlsx"]
    )

    if uploaded_file:
        original_df = read_testcases_from_excel(uploaded_file)
        st.success("Manuel test case listesi yüklendi.")

        st.subheader("Manuel Test Caseler")
        st.dataframe(original_df)

        if st.button("LLM Test Case Üret ve Karşılaştır"):
            llm_df = generate_llm_testcases("Akakçe")

            st.subheader("LLM Tarafından Üretilen Test Caseler")
            st.dataframe(llm_df)

            compare_df = compare_testcases(original_df, llm_df)

            st.subheader("Karşılaştırma Raporu")
            st.dataframe(compare_df)

            compare_df.to_excel("karsilastirma_raporu.xlsx", index=False)

            with open("karsilastirma_raporu.xlsx", "rb") as f:
                st.download_button(
                    "Karşılaştırma Raporunu İndir",
                    data=f,
                    file_name="akakce_karsilastirma_raporu.xlsx"
                )

# ---------------------------------
if __name__ == "__main__":
    main()
