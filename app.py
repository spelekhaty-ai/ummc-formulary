import streamlit as st
import pandas as pd
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Nutrition Formulary", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    df = pd.read_csv('formulary.xlsx - Sheet1.csv')
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
            return float(str(val).split()[0].replace(',', ''))
        except:
            return 0.0
            
    df['density_num'] = df['Density'].apply(to_num)
    df['protein_num'] = df['Protein (g/L)'].apply(to_num)
    
    return df

df = load_data()

# --- NAVIGATION ---
st.title("🏥 Clinical Nutrition Portal")
category = st.selectbox("Select a Section:", ["Tube Feed Formulary", "TF Goal Rate & Protein Calculator", "Oral Supplements", "Vitamin Supplements"])

st.divider()

if category == "Tube Feed Formulary":
    st.subheader("📋 Product Listing")
    search = st.text_input("🔍 Search formula name...")
    filtered_df = df[df['Product Name'].str.contains(search, case=False)]
    st.dataframe(filtered_df.drop(columns=['density_num', 'protein_num']), use_container_width=True, hide_index=True)
    
    # Download Button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Spreadsheet", data=csv, file_name='Formulary.csv', mime='text/csv')

elif category == "TF Goal Rate & Protein Calculator":
    st.subheader("🧮 Enhanced Nutrition Calculator")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 1. Goals & Meds")
        target_kcal = st.number_input("Daily Calorie Goal (kcal):", value=1800, step=50)
        target_prot = st.number_input("Daily Protein Goal (g):", value=100, step=5)
        
        st.markdown("---")
        st.markdown("#### 💊 Lipid Medications")
        propofol_rate = st.number_input("Propofol Rate (mL/hr):", min_value=0.0, value=0.0, step=1.0)
        clevidipine_rate = st.number_input("Clevidipine Rate (mL/hr):", min_value=0.0, value=0.0, step=1.0)
        
        # Calculate Med Calories
        # Propofol = 1.1 kcal/mL, Clevidipine = 2.0 kcal/mL
        propofol_kcal = propofol_rate * 24 * 1.1
        clevidipine_kcal = clevidipine_rate * 24 * 2.0
        total_med_kcal = propofol_kcal + clevidipine_kcal
        
        st.markdown("---")
        st.markdown("#### 🥤 Formula Selection")
        formula_list = df[df['Category'] == 'Formula']['Product Name'].tolist()
        choice = st.selectbox("Select Formula:", formula_list)
        
        # Pull data for choice
        row = df[df['Product Name'] == choice].iloc[0]
        density = row['density_num']
        prot_per_l = row['protein_num']
        
        hours = st.slider("Infusion Hours:", 1, 24, 24)

    with col2:
        st.markdown("### 2. Analysis")
        
        # CALORIE CALCULATION
        net_kcal_needed = target_kcal - total_med_kcal
        if net_kcal_needed < 0: net_kcal_needed = 0
        
        total_vol_day = net_kcal_needed / (density if density > 0 else 1)
        hourly_rate = total_vol_day / hours
        
        # PROTEIN CALCULATION
        # Note: If rate is rounded, recalculate protein based on actual flow
        actual_vol = round(hourly_rate) * hours
        prot_provided = (actual_vol / 1000) * prot_per_l
        prot_gap = target_prot - prot_provided

        # Display Metrics
        st.metric("Total Med Calories", f"{round(total_med_kcal)} kcal/day")
        st.metric("Goal Rate", f"{round(hourly_rate)} mL/hr")
        
        # Protein Status
        st.markdown("#### 🥩 Protein Status")
        if prot_gap > 0:
            st.error(f"Protein Gap: {round(prot_gap, 1)} g/day")
            # Suggest Modulars
            st.write("**Suggestions to fill gap:**")
            st.write(f"- Prosource TF20: {round(prot_gap/20, 1)} packets/day")
            st.write(f"- Beneprotein: {round(prot_gap/6, 1)} scoops/day")
        else:
            st.success(f"Protein Goal Met! (Provides {round(prot_provided, 1)}g)")

        # Summary Box
        st.info(f"""
        **Final Plan:**
        - **Formula:** {choice} at **{round(hourly_rate)} mL/hr** for {hours} hrs.
        - **Total Volume:** {actual_vol} mL.
        - **Kcal:** {round(actual_vol * density + total_med_kcal)} ({round(total_med_kcal)} from meds).
        - **Protein:** {round(prot_provided, 1)} g.
        """)

else:
    st.info("Section under development. Use the dropdown to navigate.")
