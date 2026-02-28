import streamlit as st
import pandas as pd
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="UMMC Nutrition Formulary", layout="wide")

# --- DATA LOADING & CLEANING ---
@st.cache_data
def load_data():
    try:
        # Load the raw CSV
        raw_df = pd.read_csv('formulary.csv')
    except:
        raw_df = pd.read_csv('formulary.xlsx - Sheet1.csv')

    # Replace all NaN/None values with empty strings for a clean UI
    raw_df = raw_df.fillna("")

    # 1. THE CARD VIEW (Formula names as columns)
    df_cards = raw_df.copy()
    df_cards.rename(columns={df_cards.columns[0]: 'Nutrient/Attribute'}, inplace=True)

    # 2. THE CALCULATION VIEW (Formula names as rows)
    df_calc = raw_df.set_index(raw_df.columns[0]).T.reset_index()
    df_calc.rename(columns={'index': 'Product Name'}, inplace=True)
    df_calc.columns = [str(c).strip() for c in df_calc.columns]
    
    # Handle duplicate "% Calories" for the calculator
    cols = list(df_calc.columns)
    count_pct = 0
    for i in range(len(cols)):
        if cols[i] == '% Calories':
            labels = ['% Cal (Prot)', '% Cal (Fat)', '% Cal (CHO)']
            if count_pct < len(labels):
                cols[i] = labels[count_pct]
                count_pct += 1
    df_calc.columns = cols

    # Helper for numbers
    def to_num(val):
        try:
            return float(str(val).split()[0].replace(',', ''))
        except:
            return 0.0
            
    df_calc['density_num'] = df_calc['Density'].apply(to_num)
    prot_col = [c for c in df_calc.columns if 'Protein (g/L)' in c]
    df_calc['protein_num'] = df_calc[prot_col[0]].apply(to_num) if prot_col else 0.0
    
    # Categorize
    modular_names = ['Prosource TF20', 'Nutrisource Fiber', 'MCT oil']
    df_calc['Category'] = df_calc['Product Name'].apply(lambda x: 'Modular' if x in modular_names else 'Formula')
    
    return df_cards, df_calc

df_cards, df_calc = load_data()

# --- NAVIGATION ---
st.title("🏥 Clinical Nutrition Portal")
category = st.selectbox("Select a Section:", ["Tube Feed Formulary (Card View)", "TF Goal Rate & Protein Calculator", "Oral Supplements", "Vitamin Supplements"])

st.divider()

# --- SECTION 1: FORMULARY (CARD VIEW) ---
if "Formulary" in category:
    st.subheader("📋 Tube Feeding Formulary Card")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        nutrient_search = st.text_input("🔍 Search Nutrients (e.g., Sodium, Fiber, MCT)...")
    with col_f2:
        all_formulas = [c for c in df_cards.columns if c != 'Nutrient/Attribute']
        selected_formulas = st.multiselect("🧪 Filter by Formula Name:", all_formulas, default=None)

    display_cards = df_cards.copy()
    
    if nutrient_search:
        display_cards = display_cards[display_cards['Nutrient/Attribute'].str.contains(nutrient_search, case=False)]
    
    if selected_formulas:
        cols_to_keep = ['Nutrient/Attribute'] + selected_formulas
        display_cards = display_cards[cols_to_keep]

    st.dataframe(display_cards, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    csv = df_cards.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Card (Spreadsheet)", data=csv, file_name='Nutrition_Card.csv', mime='text/csv')

# --- SECTION 2: CALCULATOR ---
elif category == "TF Goal Rate & Protein Calculator":
    st.subheader("🧮 Schedule & Protein Calculator")
    
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("### 1. Goals & Weight")
        use_weight = st.toggle("Calculate goals based on weight (kg)?")
        
        if use_weight:
            w_col1, w_col2, w_col3 = st.columns(3)
            with w_col1:
                weight = st.number_input("Weight (kg):", min_value=0.0, value=70.0)
            with w_col2:
                kcal_kg = st.number_input("kcal/kg:", min_value=0, value=25)
            with w_col3:
                prot_kg = st.number_input("g Pro/kg:", min_value=0.0, value=1.2, step=0.1)
            
            calc_kcal = round(weight * kcal_kg)
            calc_prot = round(weight * prot_kg)
            st.info(f"Calculated Targets: {calc_kcal} kcal | {calc_prot} g Protein")
        else:
            calc_kcal = 1800
            calc_prot = 100

        target_kcal = st.number_input("Daily Calorie Goal (kcal):", value=calc_kcal, step=50)
        target_prot = st.number_input("Daily Protein Goal (g):", value=calc_prot, step=5)
        
        st.markdown("#### 💊 Lipid Medications")
        prop_rate = st.number_input("Propofol Rate (mL/hr):", min_value=0.0, value=0.0)
        clev_rate = st.number_input("Clevidipine Rate (mL/hr):", min_value=0.0, value=0.0)
        med_kcal = (prop_rate * 24 * 1.1) + (clev_rate * 24 * 2.0)
        
        st.markdown("---")
        st.markdown("#### 🥤 Feeding Schedule")
        method = st.radio("Feeding Method:", ["Continuous/Cyclic", "Bolus"], horizontal=True)
        
        formula_list = df_calc[df_calc['Category'] == 'Formula']['Product Name'].tolist()
        choice = st.selectbox("Select Formula:", formula_list)
        
        row = df_calc[df_calc['Product Name'] == choice].iloc[0]
        density = row['density_num']
        prot_per_l = row['protein_num']
        
        if method == "Continuous/Cyclic":
            hours = st.slider("Infusion Hours per Day:", 1, 24, 24)
        else:
            num_feeds = st.number_input("Number of Feeds per Day:", min_value=1, max_value=12, value=5)

    with c2:
        st.markdown("### 2. Results")
        net_kcal = max(0, target_kcal - med_kcal)
        safe_density = density if density > 0 else 1.0
        total_vol_needed = net_kcal / safe_density
        
        if method == "Continuous/Cyclic":
            raw_rate = total_vol_needed / hours
            final_rate = int(5 * round(raw_rate / 5))
            if final_rate == 0 and raw_rate > 0: final_rate = 5
            actual_vol = final_rate * hours
            st.metric("Goal Hourly Rate", f"{final_rate} mL/hr")
        else:
            raw_bolus = total_vol_needed / num_feeds
            final_bolus = int(10 * round(raw_bolus / 10))
            if final_bolus == 0 and raw_bolus > 0: final_bolus = 10
            actual_vol = final_bolus * num_feeds
            st.metric("Volume per Feed", f"{final_bolus} mL/bolus")

        prot_provided = (actual_vol / 1000) * prot_per_l
        prot_gap = target_prot - prot_provided

        st.metric("Total Daily Volume", f"{actual_vol} mL")
        st.metric("Total Med Calories", f"{round(med_kcal)} kcal/d")
        
        st.markdown("#### 🥩 Protein Status")
        if prot_gap > 0:
            st.error(f"Protein Gap: {round(prot_gap, 1)} g/day")
            st.write(f"**To fill gap, add:**")
            st.write(f"- Prosource TF20: {round(prot_gap/20, 1)} packets")
            st.write(f"- Beneprotein: {round(prot_gap/6, 1)} scoops")
        else:
            st.success(f"Protein Goal Met! ({round(prot_provided, 1)}g provided)")

        st.info(f"**Plan Summary:** Infusing {actual_vol} mL of {choice} provides {round(actual_vol * density)} kcal and {round(prot_provided, 1)}g Protein.")
        st.warning("⚠️ Manual clinical verification required.")

else:
    st.info("Additional sections (ONS and Vitamins) can be added here.")

# --- FOOTER (Small Font at bottom of all pages) ---
st.markdown("---")
footer_html = """
<div style='text-align: left; color: gray; font-size: 0.8em;'>
    Created by: [Stacy Pelekhaty and Julie Gessler]<br>
    Last Updated: [Current Date]<br>
    Contact: [spelekhaty@umm.edu]
</div>
"""
st.markdown(footer_html, unsafe_allow_headers=True)
