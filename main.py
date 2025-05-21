import json
import os

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Finance Manager", page_icon="🏦")

CATEGORY_FILE = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "UNcategorized": []
    }

if os.path.exists(CATEGORY_FILE):
    with open(CATEGORY_FILE, "r") as f:
        st.session_state.categories = json.load(f)


def save_categories():
    with open(CATEGORY_FILE, "w") as f:
        json.dump(st.session_state.categories, f, indent=2)


def categorize_transactions(df):
    df["Category"] = "Uncategorised"

    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorised" or not keywords:
            continue

        lowered_keywords = [keyword.lower().strip() for keyword in keywords]

        for idx, row in df.iterrows():
            details = row["Details"].lower().strip()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category

    return df


def load_transactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns]
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")

        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None


def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if not keyword or keyword in st.session_state.categories[category]:
        return False
    
    st.session_state.categories[category].append(keyword)
    save_categories()
    return True


def remove_keyword_from_category(category, keyword):
    keyword = keyword.strip().lower()
    keywords = st.session_state.categories.get(category, [])

    updated_keywords = [kw for kw in keywords if kw.strip().lower() != keyword]

    if len(updated_keywords) != len(keywords):
        st.session_state.categories[category] = updated_keywords
        save_categories()


def main():
    st.title("Finance Manager")

    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])
    if uploaded_file is None:
        return
    
    df = load_transactions(uploaded_file) # data frame
    if df is None:
        return

    debits_df = df[df["Debit/Credit"] == "Debit"].copy()
    credits_df = df[df["Debit/Credit"] == "Credit"].copy() 

    st.session_state.debits_df = debits_df.copy()

    tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])
    with tab1:
        new_category = st.text_input("New Category Name")
        add_button = st.button("Add Category")

        if add_button and new_category:
            if new_category not in st.session_state.categories:
                st.session_state.categories[new_category] = []
                save_categories()
                st.rerun()

        st.subheader("Your Expenses")
        edited_df = st.data_editor(
            st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY", disabled=True),
                "Details": st.column_config.TextColumn("Details", disabled=True),
                "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED", disabled=True),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=sorted(list(st.session_state.categories.keys())),
                )
            },
            hide_index=True,
            use_container_width=True,
            key="category_editor"
        )
        
        for idx, row in edited_df.iterrows():
            new_category = row["Category"]
            last_category = st.session_state.debits_df.at[idx, "Category"]
            if new_category == last_category:
                continue
            
            details = row["Details"]
            remove_keyword_from_category(last_category, details)
            st.session_state.debits_df.at[idx, "Category"] = new_category
            result = add_keyword_to_category(new_category, details)
            
            if result:
                st.rerun()        

        st.subheader("Expense Summary")
        category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
        category_totals = category_totals.sort_values("Amount", ascending=False)

        st.dataframe(
            category_totals,
            column_config={
                "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED")
            },
            use_container_width=True,
            hide_index=True
        )

        fig = px.pie(
            category_totals,
            values="Amount",
            names="Category",
            title="Expenses by Category"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Payments Summary")
        total_payments = credits_df["Amount"].sum()
        st.metric("Total Payments", f"{total_payments:,.2f} AED")
        st.dataframe(
            credits_df[["Date", "Details", "Amount", "Status"]],
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED")
            },
            use_container_width=True,
            hide_index=True
        )


if __name__ == "__main__":
    main()