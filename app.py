import streamlit as st
import pandas as pd
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Nutrition Formulary", layout="wide")

# --- DATA LOADING & CLEANING ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('formulary.csv')
    except:
        df = pd.read_csv('formulary.xlsx - Sheet1.csv')

    df['Name'] = df['Name'].str.strip()
    df = df.set_index('Name').T.reset_index()
    df.rename(columns={'index': 'Product Name'}, inplace=True)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Fix Duplicates
    cols = list(df.columns)
    count_pct = 0
    for i in range(len(cols)):
        if cols[i] == '% Calories':
            labels = ['% Cal (Prot)', '% Cal (Fat)', '% Cal (CHO)']
            if count_pct < len(labels):
                cols[i] = labels[count_pct]
                count_pct += 1
            else:
                cols[i] = f"% Calories_{count_pct}"
                count_pct += 1
    
    final_cols = []
    counts = {}
    for col in cols:
        if col in counts:
            counts[col] += 1
            final_cols.append(f"{col}_{counts[col]}")
        else:
            counts[col] = 0
            final_cols.append(col)
    df.columns = final_cols
    
    modular_names = ['Prosource TF20', 'Nutrisource Fiber', 'MCT oil']
    df['Category'] = df['Product Name'].apply(lambda x: 'Modular' if x in modular_names else 'Formula')
    
    def to_num(val):
        try:
            return float(str(val).split()[0].replace(',', ''))
        except:
            return 0.0
            
    df['density_num'] = df['Density'].apply(to_num)
    prot_col = [c for c in df.columns if 'Protein (g/L)' in c]
    df['protein_num'] = df[prot_col[0]].apply(to_num) if prot_col else 0.0
    return df

df = load_data()

# --- NAVIGATION ---
st.title("🏥 Clinical Nutrition Portal")
category = st.selectbox("Select a Section:", ["Tube Feed Formulary", "TF Goal Rate & Protein Calculator", "Oral Supplements", "Vitamin Supplements"])

st.divider()

if df.empty:
    st.error("Data could not be loaded. Check your CSV filename on GitHub.")
    st.stop()

# --- SECTION 1: FORMULARY ---
if category in ["Tube Feed Formulas", "Tube Feed Formulary"]:
    st.subheader("📋 Product Listing")
    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        search = st.text_input("🔍 Search product name...")
    with col_s2:
        filter_cat = st.radio("Type:", ["All", "Formula", "Modular"], horizontal=True)

    filtered_df = df.copy()
    if filter_cat != "All":
        filtered_df = filtered_df[filtered_df['Category'] == filter_cat]
    if search:
        filtered_df = filtered_df[filtered_df['Product Name'].str.contains(search, case=False)]

    cols_to_show = [c for c in filtered_df.columns if c not in ['density_num', 'protein_num', 'Category']]
    st.dataframe(filtered_df[cols_to_show], use_container_width=True, hide_index=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Spreadsheet", data=csv, file_name='Nutrition_Formulary.csv', mime='text/csv')

# --- SECTION 2: CALCULATOR ---
elif category == "TF Goal Rate & Protein Calculator":
    st.subheader("🧮 Nutrition Support Calculator")
    
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("### 1. Goals & Meds")
        target_kcal = st.number_input("Daily Calorie Goal (kcal):", value=1800, step=50)
        target_prot = st.number_input("Daily Protein Goal (g):", value=100, step=5)
        
        st.markdown("#### 💊 Lipid Medications")
        prop_rate = st.number_input("Propofol Rate (mL/hr):", min_value=0.0, value=0.0)
        clev_rate = st.number_input("Clevidipine Rate (mL/hr):", min_value=0.0, value=0.0)
        med_kcal = (prop_rate * 24 * 1.1) + (clev_rate * 24 * 2.0)
        
        st.markdown("---")
        st.markdown("#### 🥤 Feeding Schedule")
        method = st.radio("Feeding Method:", ["Continuous/Cyclic", "Bolus"], horizontal=True)
        
        formula_list = df[df['Category'] == 'Formula']['Product Name'].tolist()
        choice = st.selectbox("Select Formula:", formula_list)
        
        row = df[df['Product Name'] == choice].iloc[0]
        density = row['density_num']
        prot_per_l = row['protein_num']
        
        if method == "Continuous/Cyclic":
            hours = st.slider("Infusion Hours per Day:", 1, 24, 24)
            num_feeds = 1 # Not used for continuous
        else:
            num_feeds = st.number_input("Number of Feeds per Day:", min_value=1, max_value=12, value=5)
            hours = 24 # Not used for bolus math

    with c2:
        st.markdown("### 2. Results")
        net_kcal = max(0, target_kcal - med_kcal)
        safe_density = density if density > 0 else 1.0
        total_vol_needed = net_kcal / safe_density
        
        if method == "Continuous/Cyclic":
            # Round rate to nearest 5
            raw_rate = total_vol_needed / hours
            final_rate = int(5 * round(raw_rate / 5))
            if final_rate == 0 and raw_rate > 0: final_rate = 5
            
            actual_vol = final_rate * hours
            st.metric("Goal Hourly Rate", f"{final_rate} mL/hr")
            st.metric("Total Volume", f"{actual_vol} mL/day")
            summary_txt = f"Infuse **{choice}** at **{final_rate} mL/hr** for **{hours} hours**."
        
        else:
            # Round Bolus Volume to nearest 10 for ease of measurement
            raw_bolus = total_vol_needed / num_feeds
            final_bolus = int(10 * round(raw_bolus / 10))
            if final_bolus == 0 and raw_bolus > 0: final_bolus = 10
            
            actual_vol = final_bolus * num_feeds
            st.metric("Volume per Feed", f"{final_bolus} mL/bolus")
            st.metric("Total Volume", f"{actual_vol} mL/day")
            summary_txt = f"Provide **{final_bolus} mL** of **{choice}**, **{num_feeds} times per day**."

        # Protein Check
        prot_provided = (actual_vol / 1000) * prot_per_l
        prot_gap = target_prot - prot_provided

        st.markdown("#### 🥩 Protein Status")
        if prot_gap > 0:
            st.error(f"Protein Gap: {round(prot_gap, 1)} g/day")
            st.write(f"**Modular Suggestions:**")
            st.write(f"- Prosource TF20: {round(prot_gap/20, 1)} packets")
        else:
            st.success(f"Protein Goal Met! ({round(prot_provided, 1)}g provided)")

        st.info(f"**Plan Summary:** {summary_txt}")
        st.warning("⚠️ Manual clinical verification required.")

else:
    st.info("Additional sections (ONS and Vitamins) can be added here.")
