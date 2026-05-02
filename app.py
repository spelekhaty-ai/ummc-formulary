import streamlit as st
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Nutrition Formulary", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    try:
        df_tf_raw = pd.read_csv('formulary.csv')
    except:
        try:
            df_tf_raw = pd.read_csv('formulary.xlsx - Sheet1.csv')
        except:
            df_tf_raw = pd.DataFrame()

    try:
        df_ons_raw = pd.read_csv('supplement_formulary.csv')
    except:
        df_ons_raw = pd.DataFrame()

    def process_formulary(df):
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        df = df.fillna("")
        
        # Card View (For display)
        df_cards = df.copy()
        df_cards.rename(columns={df_cards.columns[0]: 'Nutrient/Attribute'}, inplace=True)

        # Calc View (For math/backend)
        df_calc = df.set_index(df.columns[0]).T.reset_index()
        df_calc.rename(columns={'index': 'Product Name'}, inplace=True)
        df_calc.columns = [str(c).replace('\n', ' ').strip() for c in df_calc.columns]
        
        cols = list(df_calc.columns)
        count_pct = 0
        for i in range(len(cols)):
            if cols[i] == '% Calories':
                labels = ['% Cal (Prot)', '% Cal (Fat)', '% Cal (CHO)']
                if count_pct < len(labels):
                    cols[i] = labels[count_pct]
                    count_pct += 1
        df_calc.columns = cols

        def to_num(val):
            try:
                return float(str(val).split()[0].replace(',', ''))
            except:
                return 0.0
                
        if 'Density' in df_calc.columns:
            df_calc['density_num'] = df_calc['Density'].apply(to_num)
        
        prot_col = [c for c in df_calc.columns if 'Protein' in c and '(g/L)' in c]
        if not prot_col:
            prot_col = [c for c in df_calc.columns if 'Protein' in c]
            
        if prot_col:
            df_calc['protein_num'] = df_calc[prot_col[0]].apply(to_num)
        else:
            df_calc['protein_num'] = 0.0
        
        modular_names = ['Prosource TF20', 'Nutrisource Fiber', 'MCT oil']
        df_calc['Category'] = df_calc['Product Name'].apply(lambda x: 'Modular' if x in modular_names else 'Formula')
        
        return df_cards, df_calc

    df_cards_tf, df_calc_tf, df_cards_ons, df_calc_ons = process_formulary(df_tf_raw)[0], process_formulary(df_tf_raw)[1], process_formulary(df_ons_raw)[0], process_formulary(df_ons_raw)[1]
    
    return df_cards_tf, df_calc_tf, df_cards_ons, df_calc_ons

df_cards_tf, df_calc_tf, df_cards_ons, df_calc_ons = load_data()

# --- NAVIGATION ---
st.title("🏥 UMMC Clinical Nutrition Portal")
category = st.selectbox("Select a Section:", ["Tube Feed Formulary (Card View)", "Oral Supplement Formulary (Card View)", "TF Goal Rate & Protein Calculator", "Vitamin Supplements"])

st.divider()

# --- CUSTOM CSS FOR SCROLLING + WRAPPING ---
# This style block ensures columns don't squish but text still wraps
st.markdown("""
    <style>
        .scroll-container {
            overflow-x: auto;
            width: 100%;
            border: 1px solid #e6e9ef;
            border-radius: 5px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            font-size: 14px;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #e6e9ef;
            border-right: 1px solid #e6e9ef;
            min-width: 180px; /* Prevents columns from getting too thin */
            max-width: 300px; /* Prevents columns from getting too wide */
            white-space: normal !important; /* FORCES WRAP */
            word-wrap: break-word;
            vertical-align: top;
        }
        th {
            background-color: #f8f9fb;
            color: #31333F;
            font-weight: bold;
            position: sticky;
            top: 0;
        }
        tr:hover {background-color: #f1f3f6;}
    </style>
""", unsafe_allow_html=True)

# --- SECTION: TUBE FEED FORMULARY ---
if category == "Tube Feed Formulary (Card View)":
    if df_cards_tf.empty:
        st.error("Tube Feed data not found.")
    else:
        st.subheader("📋 Tube Feeding Formulary Card")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            nutrient_search = st.text_input("🔍 Search Nutrients (e.g., Sodium, Fiber)...", key="tf_nut_search")
        with col_f2:
            all_formulas = [c for c in df_cards_tf.columns if c != 'Nutrient/Attribute']
            selected_formulas = st.multiselect("🧪 Filter Formulas:", all_formulas, key="tf_form_filter")
        
        display_cards = df_cards_tf.copy()
        if nutrient_search:
            display_cards = display_cards[display_cards['Nutrient/Attribute'].str.contains(nutrient_search, case=False)]
        if selected_formulas:
            display_cards = display_cards[['Nutrient/Attribute'] + selected_formulas]
        
        # --- SCROLLABLE WRAPPED TABLE ---
        st.write(f'<div class="scroll-container">{display_cards.to_html(index=False, escape=False)}</div>', unsafe_allow_html=True)

# --- SECTION: ORAL SUPPLEMENT FORMULARY ---
elif category == "Oral Supplement Formulary (Card View)":
    if df_cards_ons.empty:
        st.error("Oral Supplement data not found.")
    else:
        st.subheader("🥤 Oral Supplement Formulary Card")
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            ons_nutrient_search = st.text_input("🔍 Search Nutrients...", key="ons_nut_search")
        with col_o2:
            all_ons = [c for c in df_cards_ons.columns if c != 'Nutrient/Attribute']
            selected_ons = st.multiselect("🥤 Filter Supplements:", all_ons, key="ons_filter")
        
        display_ons = df_cards_ons.copy()
        if ons_nutrient_search:
            display_ons = display_ons[display_ons['Nutrient/Attribute'].str.contains(ons_nutrient_search, case=False)]
        if selected_ons:
            display_ons = display_ons[['Nutrient/Attribute'] + selected_ons]
        
        # --- SCROLLABLE WRAPPED TABLE ---
        st.write(f'<div class="scroll-container">{display_ons.to_html(index=False, escape=False)}</div>', unsafe_allow_html=True)

# --- SECTION: CALCULATOR ---
elif category == "TF Goal Rate & Protein Calculator":
    if df_calc_tf.empty:
        st.error("Tube Feed data required for calculator.")
    else:
        st.subheader("🧮 Schedule & Protein Calculator")
        
        # --- NEW: SELECTION GUIDANCE EXPANDER ---
        with st.expander("📖 View Formula Selection Guidance"):
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                st.markdown("**Standard**")
                st.caption("> **Jevity 1.5: Normal GI function\n | Osmolite 1.5: Low fiber needs**")
            with g2:
                st.markdown("**ICU**")
                st.caption("> **Vital High Protein: CRRT, ECMO, high rate propofol\n | Vital AF 1.2: SCI, malabsorption, low carb\n | Peptamen 1.5: malabsorption\n |  Pivot 1.5: Trauma, TBI**")
            with g3:
                st.markdown("**Specialized**")
                st.caption("> **Nepro: Low electrolyte, low carb\n | Glucerna 1.5: low carb, polymeric\n | Vital AF 1.2: low carb, semi-elemental**")
            with g4:
                st.markdown("**Allergy & Culture**")
                st.caption("> **Kate Farms (all): Vegan, Kosher, free from top 8 allergens\n | All: gluten and lactose free\n | Vital + Pivot: NOT Kosher**")               
        col1, col2 = st.columns([1, 1])

        # --- MODE TOGGLE ---
        calc_mode = st.radio("Calculator Mode:", ["Calculate Goal Rate", "Check Current Provision"], horizontal=True)
        st.divider()

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("### 1. Patient Goals")
            
            # Weight is outside the toggle so it's always available for math
            weight = st.number_input("Weight (kg):", min_value=1.0, value=70.0, step=1.0)
            
            use_weight_goals = st.toggle("Calculate targets based on weight?", value=True)
            
            if use_weight_goals:
                w_col1, w_col2 = st.columns(2)
                with w_col1:
                    kcal_kg_input = st.number_input("kcal/kg:", min_value=0, value=20, step=1)
                with w_col2:
                    prot_kg_input = st.number_input("g Pro/kg:", min_value=0.0, value=1.2, step=0.1)
                
                calc_kcal = round(weight * kcal_kg_input)
                calc_prot = round(weight * prot_kg_input)
                st.info(f"**|** Targets: {calc_kcal} kcal | {calc_prot} g Protein")
            else:
                calc_kcal, calc_prot = 1800, 100

            target_kcal = st.number_input("Goal kcal/day:", value=int(calc_kcal), step=50)
            target_prot = st.number_input("Goal g Pro/day:", value=int(calc_prot), step=5)

            st.markdown("#### 💊 Lipid Medications")
            med_units = st.radio("Enter Dose In:", ["mL/hr", "mcg/min"], horizontal=True)
            m_col1, m_col2 = st.columns(2)
            
            if med_units == "mL/hr":
                with m_col1: p_rate = st.number_input("Propofol (mL/hr):", min_value=0.0, value=0.0, step=1.0)
                with m_col2: c_rate = st.number_input("Clevidipine (mL/hr):", min_value=0.0, value=0.0, step=1.0)
            else:
                with m_col1: 
                    p_mcg = st.number_input("Propofol (mcg/min):", min_value=0.0, value=0.0, step=5.0)
                    p_rate = (p_mcg * 60) / 10000
                with m_col2:
                    c_mcg = st.number_input("Clevidipine (mcg/min):", min_value=0.0, value=0.0, step=1.0)
                    c_rate = (c_mcg * 60) / 500
            
            med_kcal = (p_rate * 24 * 1.1) + (c_rate * 24 * 2.0)

        with col2:
            st.markdown("### 2. Infusion Details")
            formula_list = df_calc_tf['Product Name'].tolist()
            choice = st.selectbox("Select Formula:", formula_list)
            
            row = df_calc_tf[df_calc_tf['Product Name'] == choice].iloc[0]
            dens, prot_l = row['density_num'], row['protein_num']
            
            # Water content logic
            water_col = [c for c in df_calc_tf.columns if 'Water' in c]
            def clean_w(v):
                try: return float(str(v).replace('%', '').strip()) / 100
                except: return 0.8
            w_factor = clean_w(row[water_col[0]]) if water_col else 0.8

            prosource_prot = 0.0

            if calc_mode == "Calculate Goal Rate":
                method = st.radio("Schedule Type:", ["Continuous/Cyclic", "Bolus"], horizontal=True, key="goal_method")
                if method == "Continuous/Cyclic":
                    hours = st.slider("Infusion Hours per Day:", 1, 24, 24)
                    net_kcal = max(0, target_kcal - med_kcal)
                    vol_needed = net_kcal / (dens if dens > 0 else 1)
                    final_val = int(5 * round((vol_needed / hours) / 5))
                    if final_val == 0 and vol_needed > 0: final_val = 5
                    actual_vol = final_val * hours
                    st.metric("Goal Hourly Rate", f"{final_val} mL/hr")
                else:
                    num_feeds = st.number_input("Feeds per Day:", min_value=1, max_value=8, value=4)
                    net_kcal = max(0, target_kcal - med_kcal)
                    vol_needed = net_kcal / (dens if dens > 0 else 1)
                    final_bolus = int(10 * round((vol_needed / num_feeds) / 10))
                    actual_vol = final_bolus * num_feeds
                    st.metric("Volume per Feed", f"{final_bolus} mL/bolus")
            else:
                i_col1, i_col2 = st.columns(2)
                with i_col1: rate_entry = st.number_input("Current Rate (mL/hr):", min_value=0, value=60, step=5)
                with i_col2: hours_entry = st.number_input("Hours per Day:", min_value=1, max_value=24, value=24)
                actual_vol = rate_entry * hours_entry
                
                st.markdown("#### ➕ Modulars")
                if st.checkbox("Including ProSource TF20?"):
                    pkts = st.number_input("Packets per day:", min_value=0.5, value=1.0, step=0.5)
                    prosource_prot = pkts * 20.0

            # Final Summary Math
            prosource_kcal = (prosource_prot / 20) * 100
            total_kcal = (actual_vol * dens) + med_kcal + prosource_kcal
            total_prot = ((actual_vol / 1000) * prot_l) + prosource_prot
            free_water = actual_vol * w_factor

            st.divider()
            st.markdown("### 3. Summary of Provision")
            res1, res2, res3 = st.columns(3)
            with res1:
                st.metric("Calories", f"{round(total_kcal)} kcal")
                st.caption(f"| {round((total_kcal / target_kcal) * 100)}% Goal")
                st.caption(f"| {round(total_kcal / weight, 1)} kcal/kg")
            with res2:
                st.metric("Protein", f"{round(total_prot, 1)} g")
                st.caption(f"| {round((total_prot / target_prot) * 100)}% Goal")
                st.caption(f"| {round(total_prot / weight, 1)} g/kg")
            with res3:
                st.metric("Free Water", f"{round(free_water)} mL")
                st.caption(f"| {round(free_water / weight, 1)} mL/kg")
                st.caption(f"| Total Vol: {actual_vol} mL")

            prot_gap = target_prot - total_prot
            if calc_mode == "Calculate Goal Rate" and prot_gap > 0.5:
                st.error(f"**Protein Gap:** {round(prot_gap, 1)} g/day")
                pkts_needed = round(prot_gap / 20, 1)
                st.info(f"**Recommendation:** Provide **{pkts_needed}** pkts of Prosource TF20.")
            elif prot_gap <= 0.5:
                st.success(f"✅ Regimen Meets Goals")
            else:
                st.warning(f"Remaining Protein Deficit: {round(prot_gap, 1)} g/day")
                
else:
    st.info("Additional sections will be added here.")

# --- FOOTER ---
st.divider()
st.caption("Created by: Stacy Pelekhaty and Julie Gessler")
st.caption("Last Updated: 5.2026")
st.caption("Contact: spelekhaty@umm.edu")
