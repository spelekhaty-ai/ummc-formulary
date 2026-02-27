import streamlit as st
import pandas as pd
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Nutrition Formulary", layout="wide")

# --- DATA LOADING & CLEANING ---
@st.cache_data
def load_data():
    try:
        # Try the renamed file first
        df = pd.read_csv('formulary.csv')
    except:
        # Fallback to the original long name if not renamed yet
        df = pd.read_csv('formulary.xlsx - Sheet1.csv')

    # 1. Clean the 'Name' column so we can use it as an index
    df['Name'] = df['Name'].str.strip()
    
    # 2. Transpose the data (make products the rows)
    df = df.set_index('Name').T.reset_index()
    df.rename(columns={'index': 'Product Name'}, inplace=True)
    
    # 3. Clean column headers (remove spaces/newlines)
    df.columns = [str(c).strip() for c in df.columns]
    
    # 4. FIX DUPLICATE COLUMNS (The cause of your error)
    cols = list(df.columns)
    count_pct = 0
    for i in range(len(cols)):
        if cols[i] == '% Calories':
            # Map them in order: Protein, then Fat, then CHO
            labels = ['% Cal (Prot)', '% Cal (Fat)', '% Cal (CHO)']
            if count_pct < len(labels):
                cols[i] = labels[count_pct]
                count_pct += 1
            else:
                cols[i] = f"% Calories_{count_pct}"
                count_pct += 1
    
    # 5. Generic de-duplicator (just in case there are other duplicates)
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
    
    # 6. Categorize Modulars
    modular_names = ['Prosource TF20', 'Nutrisource Fiber', 'MCT oil']
    df['Category'] = df['Product Name'].apply(lambda x: 'Modular' if x in modular_names else 'Formula')
    
    # 7. Create numeric columns for the calculator
    def to_num(val):
        try:
            # Handle cases like "1.5 kcal/mL" or "63.8"
            return float(str(val).split()[0].replace(',', ''))
        except:
            return 0.0
            
    df['density_num'] = df['Density'].apply(to_num)
    
    # Find the protein column even if name varies slightly
    prot_col = [c for c in df.columns if 'Protein (g/L)' in c]
    if prot_col:
        df['protein_num'] = df[prot_col[0]].apply(to_num)
    else:
        df['protein_num'] = 0.0
        
    return df

# Initialize Data
df = load_data()

# --- NAVIGATION ---
st.title("🏥 Clinical Nutrition Portal")
category = st.selectbox("Select a Section:", ["Tube Feed Formulary", "TF Goal Rate & Protein Calculator", "Oral Supplements", "Vitamin Supplements"])

st.divider()

if df.empty:
    st.error("Data could not be loaded. Check your CSV filename on GitHub.")
    st.stop()

# --- SECTION 1: FORMULARY ---
if category == "Tube Feed Formulary":
    st.subheader("📋 Product Listing")
    
    # Search & Filter
    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        search = st.text_input("🔍 Search product name...", placeholder="e.g. Jevity, Vital, Kate...")
    with col_s2:
        filter_cat = st.radio("Type:", ["All", "Formula", "Modular"], horizontal=True)

    # Filter Logic
    filtered_df = df.copy()
    if filter_cat != "All":
        filtered_df = filtered_df[filtered_df['Category'] == filter_cat]
    if search:
        filtered_df = filtered_df[filtered_df['Product Name'].str.contains(search, case=False)]

    # Display the table (dropping the hidden calculation columns)
    cols_to_show = [c for c in filtered_df.columns if c not in ['density_num', 'protein_num', 'Category']]
    st.dataframe(filtered_df[cols_to_show], use_container_width=True, hide_index=True)
    
    # Download Button
    st.markdown("---")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Full Spreadsheet", data=csv, file_name='Nutrition_Formulary.csv', mime='text/csv')

# --- SECTION 2: CALCULATOR ---
elif category == "TF Goal Rate & Protein Calculator":
    st.subheader("🧮 Enhanced Nutrition Calculator")
    
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("### 1. Goals & Meds")
        target_kcal = st.number_input("Daily Calorie Goal (kcal):", value=1800, step=50)
        target_prot = st.number_input("Daily Protein Goal (g):", value=100, step=5)
        
        st.markdown("#### 💊 Lipid Medications")
        prop_rate = st.number_input("Propofol Rate (mL/hr):", min_value=0.0, value=0.0)
        clev_rate = st.number_input("Clevidipine Rate (mL/hr):", min_value=0.0, value=0.0)
        
        med_kcal = (prop_rate * 24 * 1.1) + (clev_rate * 24 * 2.0)
        
        st.markdown("#### 🥤 Formula Selection")
        formula_list = df[df['Category'] == 'Formula']['Product Name'].tolist()
        choice = st.selectbox("Select Formula:", formula_list)
        
        row = df[df['Product Name'] == choice].iloc[0]
        density = row['density_num']
        prot_per_l = row['protein_num']
        
        hours = st.slider("Infusion Hours:", 1, 24, 24)

    with c2:
        st.markdown("### 2. Analysis")
        net_kcal = max(0, target_kcal - med_kcal)
        total_vol = net_kcal / (density if density > 0 else 1)
        
        rounded_rate = round(total_vol / hours)
        actual_vol = rounded_rate * hours
        prot_provided = (actual_vol / 1000) * prot_per_l
        prot_gap = target_prot - prot_provided

        st.metric("Total Med Calories", f"{round(med_kcal)} kcal/d")
        st.metric("Goal Rate", f"{rounded_rate} mL/hr")
        
        st.markdown("#### 🥩 Protein Status")
        if prot_gap > 0:
            st.error(f"Protein Gap: {round(prot_gap, 1)} g/day")
            st.write(f"**Modular Suggestions:**")
            st.write(f"- Prosource TF20 (20g): {round(prot_gap/20, 1)} packets")
            st.write(f"- Beneprotein (6g): {round(prot_gap/6, 1)} scoops")
        else:
            st.success(f"Protein Goal Met! ({round(prot_provided, 1)}g provided)")

        st.info(f"**Final Plan:** Infuse {choice} at {rounded_rate} mL/hr for {hours} hours.")

else:
    st.info("Additional sections (ONS and Vitamins) can be built out using the same logic as the TF section.")
