import streamlit as st
import pandas as pd
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Nutrition Formulary", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # We are looking for the renamed file 'formulary.csv'
    try:
        df = pd.read_csv('formulary.csv')
    except FileNotFoundError:
        st.error("File 'formulary.csv' not found. Please ensure it is uploaded to GitHub.")
        return pd.DataFrame()

    # Transpose so products are rows
    df = df.set_index('Name').T.reset_index()
    df.rename(columns={'index': 'Product Name'}, inplace=True)
    
    # Clean column names
    df.columns = [c.strip() for c in df.columns]
    
    # Categorize Modulars
    modular_names = ['Prosource TF20', 'Nutrisource Fiber', 'MCT oil']
    df['Category'] = df['Product Name'].apply(lambda x: 'Modular' if x in modular_names else 'Formula')
    
    # Helper for numbers
    def to_num(val):
        try:
            # Removes "kcal/mL", commas, and spaces to get the raw number
            return float(str(val).split()[0].replace(',', ''))
        except:
            return 0.0
            
    df['density_num'] = df['Density'].apply(to_num)
    # Finding the Protein column (it might have spaces or units)
    prot_col = [c for c in df.columns if 'Protein (g/L)' in c][0]
    df['protein_num'] = df[prot_col].apply(to_num)
    
    return df

df = load_data()

# --- NAVIGATION ---
st.title("🏥 Clinical Nutrition Portal")
category = st.selectbox("Select a Section:", ["Tube Feed Formulary", "TF Goal Rate & Protein Calculator", "Oral Supplements", "Vitamin Supplements"])

st.divider()

if df.empty:
    st.warning("Please upload 'formulary.csv' to your GitHub repository to activate the app.")
    st.stop()

# --- SECTION 1: FORMULARY ---
if category == "Tube Feed Formulary":
    st.subheader("📋 Product Listing")
    search = st.text_input("🔍 Search formula name...")
    filtered_df = df[df['Product Name'].str.contains(search, case=False)]
    st.dataframe(filtered_df.drop(columns=['density_num', 'protein_num']), use_container_width=True, hide_index=True)
    
    # Download Button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Spreadsheet", data=csv, file_name='Nutrition_Formulary.csv', mime='text/csv')

# --- SECTION 2: CALCULATOR ---
elif category == "TF Goal Rate & Protein Calculator":
    st.subheader("🧮 Enhanced Nutrition Calculator")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 1. Goals & Meds")
        target_kcal = st.number_input("Daily Calorie Goal (kcal):", value=1800, step=50)
        target_prot = st.number_input("Daily Protein Goal (g):", value=100, step=5)
        
        st.markdown("---")
        st.markdown("#### 💊 Lipid Medications")
        prop_rate = st.number_input("Propofol Rate (mL/hr):", min_value=0.0, value=0.0)
        clev_rate = st.number_input("Clevidipine Rate (mL/hr):", min_value=0.0, value=0.0)
        
        # Math: Propofol (1.1 kcal/mL), Clevidipine (2.0 kcal/mL)
        med_kcal = (prop_rate * 24 * 1.1) + (clev_rate * 24 * 2.0)
        
        st.markdown("---")
        st.markdown("#### 🥤 Formula Selection")
        formula_list = df[df['Category'] == 'Formula']['Product Name'].tolist()
        choice = st.selectbox("Select Formula:", formula_list)
        
        row = df[df['Product Name'] == choice].iloc[0]
        density = row['density_num']
        prot_per_l = row['protein_num']
        
        hours = st.slider("Infusion Hours:", 1, 24, 24)

    with col2:
        st.markdown("### 2. Analysis")
        
        net_kcal = max(0, target_kcal - med_kcal)
        total_vol = net_kcal / (density if density > 0 else 1)
        rate = total_vol / hours
        
        # Actual delivery based on rounded rate
        rounded_rate = round(rate)
        actual_vol = rounded_rate * hours
        prot_provided = (actual_vol / 1000) * prot_per_l
        prot_gap = target_prot - prot_provided

        st.metric("Total Med Calories", f"{round(med_kcal)} kcal/d")
        st.metric("Goal Rate", f"{rounded_rate} mL/hr")
        
        st.markdown("#### 🥩 Protein Status")
        if prot_gap > 0:
            st.error(f"Protein Gap: {round(prot_gap, 1)} g/day")
            st.write(f"**To fill gap, add:**")
            st.write(f"- Prosource TF20: {round(prot_gap/20, 1)} packets")
            st.write(f"- Beneprotein: {round(prot_gap/6, 1)} scoops")
        else:
            st.success(f"Protein Goal Met! ({round(prot_provided, 1)}g provided)")

        st.info(f"**Plan Summary:** Infuse {choice} at {rounded_rate} mL/hr for {hours} hours.")

else:
    st.subheader(f"📂 {category}")
    st.info("Section for future protocols and supplements.")
