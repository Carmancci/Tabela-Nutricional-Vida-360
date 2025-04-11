# nutri_app.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
import math

# --- Configuração da Página ---
# Esta deve ser a primeira chamada Streamlit, sem indentação
st.set_page_config(layout="wide", page_title="Saúde Vida 360")

# --- Funções de Cálculo de Composição Corporal ---
# Definições de função devem começar na coluna 0
def calculate_bmi(weight_kg, height_cm):
    # Código dentro da função DEVE ser indentado
    if height_cm <= 0: return None
    try:
        height_m = float(height_cm) / 100.0
        bmi = float(weight_kg) / (height_m ** 2)
        return bmi
    except (ValueError, TypeError):
        return None

def classify_bmi(bmi):
    if bmi is None: return "N/A"
    if bmi < 18.5: return "Baixo Peso"
    elif 18.5 <= bmi < 24.9: return "Peso Normal"
    elif 25 <= bmi < 29.9: return "Sobrepeso"
    elif 30 <= bmi < 34.9: return "Obesidade Grau I"
    elif 35 <= bmi < 39.9: return "Obesidade Grau II"
    else: return "Obesidade Grau III"

def calculate_bf_us_navy(sexo, height_cm, neck_cm, waist_cm, hip_cm=None):
    try:
        height_cm_f = float(height_cm); neck_cm_f = float(neck_cm); waist_cm_f = float(waist_cm)
        if height_cm_f <= 0 or neck_cm_f <= 0 or waist_cm_f <= 0: st.warning("Altura/Pescoço/Cintura > 0."); return None
        if sexo.lower() == 'masculino':
            bf_percent = 86.010 * math.log10(waist_cm_f - neck_cm_f) - 70.041 * math.log10(height_cm_f) + 36.76
        elif sexo.lower() == 'feminino':
            if hip_cm is None or float(hip_cm) <= 0: st.warning("Quadril necessário (F)."); return None
            hip_cm_f = float(hip_cm)
            bf_percent = 163.205 * math.log10(waist_cm_f + hip_cm_f - neck_cm_f) - 97.684 * math.log10(height_cm_f) - 78.387
        else: st.error("Sexo inválido (US Navy)."); return None
        return max(bf_percent, 0.0)
    except (ValueError, TypeError, OverflowError):
        st.error("Erro cálculo BF% (US Navy).")
        return None

def estimate_bf_from_bmi(bmi, age, sexo):
    if bmi is None or age <= 0: return None
    try:
        bmi_f = float(bmi); age_i = int(age); sex_factor = 1 if sexo.lower() == 'masculino' else 0
        bf_percent = (1.20 * bmi_f) + (0.23 * age_i) - (10.8 * sex_factor) - 5.4; return max(bf_percent, 0.0)
    except (ValueError, TypeError):
        return None

def calcular_bf_jp3(sexo, idade, dobras_mm):
    try:
        idade = int(idade); dobras_float = {k: float(v) for k, v in dobras_mm.items()}; soma_dobras = sum(dobras_float.values())
        if soma_dobras <= 0 or idade <= 0: st.warning("Valores inválidos dobras/idade."); return None
        if sexo.lower() == 'masculino':
            if not all(k in dobras_float for k in ['peitoral', 'abdomen', 'coxa']): st.error("Dobras incorretas (M)."); return None
            densidade = 1.10938 - (0.0008267 * soma_dobras) + (0.0000016 * (soma_dobras ** 2)) - (0.0002574 * idade)
        elif sexo.lower() == 'feminino':
            if not all(k in dobras_float for k in ['triceps', 'suprailiaca', 'coxa']): st.error("Dobras incorretas (F)."); return None
            densidade = 1.0994921 - (0.0009929 * soma_dobras) + (0.0000023 * (soma_dobras ** 2)) - (0.0001392 * idade)
        else: st.error("Sexo inválido."); return None
        if densidade <= 0: st.warning("Densidade inválida."); return None
        percentual_gordura = ((4.95 / densidade) - 4.50) * 100; return max(percentual_gordura, 0.0)
    except (ValueError, TypeError, KeyError) as e: st.error(f"Erro BF% (Dobras): {e}."); return None

# --- Funções de Cálculo Nutricional ---
def calcular_lbm(peso_kg, percentual_gordura):
    if percentual_gordura is None: return None
    try:
        peso_kg_f = float(peso_kg); percentual_gordura_f = float(percentual_gordura)
        if np.isnan(percentual_gordura_f) or percentual_gordura_f <= 0 or percentual_gordura_f >= 100: return None
        gc_decimal = percentual_gordura_f / 100.0; lbm = peso_kg_f * (1 - gc_decimal); return lbm
    except (ValueError, TypeError): return None

def calcular_tmb(peso_kg, altura_cm, idade_anos, sexo, lbm_kg=None):
    try:
        peso_kg_f = float(peso_kg); altura_cm_f = float(altura_cm); idade_anos_i = int(idade_anos)
        if lbm_kg is not None and lbm_kg > 0:
            tmb = 370 + (21.6 * float(lbm_kg)); st.session_state.tmb_formula = "Katch-McArdle (com % Gordura)"; return tmb
        else:
            if sexo.lower() == 'masculino': tmb = (10 * peso_kg_f) + (6.25 * altura_cm_f) - (5 * idade_anos_i) + 5
            elif sexo.lower() == 'feminino': tmb = (10 * peso_kg_f) + (6.25 * altura_cm_f) - (5 * idade_anos_i) - 161
            else: st.warning("Sexo inválido."); return None
            st.session_state.tmb_formula = "Mifflin-St Jeor (sem % Gordura)"; return tmb
    except (ValueError, TypeError): st.error("Erro TMB."); return None

def calcular_get(tmb, nivel_atividade):
    fatores_atividade = {'Sedentário (Pouco ou nenhum exercício)': 1.2, 'Levemente Ativo (Exercício leve 1-3 dias/semana)': 1.375, 'Moderadamente Ativo (Exercício moderado 3-5 dias/semana)': 1.55, 'Muito Ativo (Exercício intenso 6-7 dias/semana)': 1.725, 'Extremamente Ativo (Exercício muito intenso + trabalho físico)': 1.9}
    fator = fatores_atividade.get(nivel_atividade, 1.2)
    try: get = float(tmb) * fator; st.session_state.activity_factor = fator; return get
    except (ValueError, TypeError): st.error("Erro GET."); return None

def calcular_macros(get, peso_kg, meta_proteina_g_kg, meta_gordura_percent):
    try:
        get_f = float(get); peso_kg_f = float(peso_kg); meta_proteina_g_kg_f = float(meta_proteina_g_kg); meta_gordura_percent_f = float(meta_gordura_percent)
        if get_f <= 0 or peso_kg_f <=0 or meta_proteina_g_kg_f <=0 or meta_gordura_percent_f < 0 or meta_gordura_percent_f >= 100: st.error("Valores inválidos macros."); return None, None, None, None
        proteina_g = peso_kg_f * meta_proteina_g_kg_f; calorias_proteina = proteina_g * 4
        gordura_g = (get_f * (meta_gordura_percent_f / 100.0)) / 9; calorias_gordura = gordura_g * 9
        calorias_carb = get_f - calorias_proteina - calorias_gordura; carboidrato_g = calorias_carb / 4
        if carboidrato_g < 0: st.warning("Aviso: Carbs negativos -> ajustando para 0g."); carboidrato_g = 0; calorias_carb = 0
        return get_f, proteina_g, carboidrato_g, gordura_g
    except (ValueError, TypeError): st.error("Erro valores macros."); return None, None, None, None

# --- Carregar Banco de Dados de Alimentos ---
@st.cache_data
def load_food_database(file_path="taco_completa.xlsx"):
    try:
        if file_path.endswith('.csv'): df = pd.read_csv(file_path, header=1)
        elif file_path.endswith('.xlsx'): header_row_index = 2; df = pd.read_excel(file_path, header=header_row_index)
        else: st.error("Formato de arquivo não suportado."); return pd.DataFrame()
        df = df.rename(columns={'Descrição dos alimentos': 'Nome_Alimento','(kcal)': 'Energia_kcal_100g','(g)': 'Proteina_g_100g','(g).1': 'Lipideos_g_100g','(g).3': 'Carboidrato_g_100g',})
        required_cols = ['Nome_Alimento', 'Energia_kcal_100g', 'Proteina_g_100g', 'Carboidrato_g_100g', 'Lipideos_g_100g']
        cols_found_after_rename = df.columns.tolist()
        if not all(col in cols_found_after_rename for col in required_cols):
            missing_cols = [col for col in required_cols if col not in cols_found_after_rename]; st.error(f"Erro Crítico: Colunas não encontradas: {missing_cols}. Verifique df.rename()."); return pd.DataFrame()
        for col in required_cols[1:]: df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce')
        df.dropna(subset=required_cols, inplace=True); df['Nome_Alimento'] = df['Nome_Alimento'].astype(str).str.strip(); df = df[~df['Nome_Alimento'].str.isnumeric()]; df = df[df['Nome_Alimento'].str.len() > 0]; df = df[~df['Nome_Alimento'].str.contains("Descrição dos alimentos", case=False, na=False)]; df = df.sort_values(by='Nome_Alimento'); return df
    except FileNotFoundError: st.error(f"Erro Crítico: Arquivo '{file_path}' não encontrado."); return pd.DataFrame()
    except Exception as e:
        if "Missing optional dependency 'openpyxl'" in str(e): st.error("Erro: 'openpyxl' não instalado.")
        else: st.error(f"Erro ao carregar arquivo: {e}"); return pd.DataFrame()

# --- Banco de Dados de Suplementos Pré-definidos ---
PREDEFINED_SUPPLEMENTS = {
    "Whey Protein Concentrado (média)": {"kcal_g": 4.0, "p_g": 0.80, "c_g": 0.08, "l_g": 0.07, "ca_mg_g": 1.2, "fe_mg_g": 0.01},
    "Whey Protein Isolado (média)": {"kcal_g": 3.8, "p_g": 0.90, "c_g": 0.01, "l_g": 0.01, "ca_mg_g": 0.5, "fe_mg_g": 0.01},
    "Caseína Micelar (média)": {"kcal_g": 3.7, "p_g": 0.80, "c_g": 0.05, "l_g": 0.02, "ca_mg_g": 2.0, "fe_mg_g": 0.01},
    "Creatina Monohidratada": {"kcal_g": 0.0, "p_g": 0.0, "c_g": 0.0, "l_g": 0.0, "ca_mg_g": 0.0, "fe_mg_g": 0.0},
    "Maltodextrina": {"kcal_g": 4.0, "p_g": 0.0, "c_g": 1.0, "l_g": 0.0, "ca_mg_g": 0.0, "fe_mg_g": 0.0},
    "Dextrose": {"kcal_g": 4.0, "p_g": 0.0, "c_g": 1.0, "l_g": 0.0, "ca_mg_g": 0.0, "fe_mg_g": 0.0},
    "Cafeína Anidra": {"kcal_g": 0.0, "p_g": 0.0, "c_g": 0.0, "l_g": 0.0, "ca_mg_g": 0.0, "fe_mg_g": 0.0},
    "Beta-Alanina": {"kcal_g": 0.0, "p_g": 0.0, "c_g": 0.0, "l_g": 0.0, "ca_mg_g": 0.0, "fe_mg_g": 0.0},
}

# Carrega o banco de dados de alimentos
food_db = load_food_database()

# --- Inicialização do Estado da Sessão ---
if 'logged_foods' not in st.session_state: st.session_state.logged_foods = []
if 'logged_supplements' not in st.session_state: st.session_state.logged_supplements = []
if 'custom_supplements' not in st.session_state: st.session_state.custom_supplements = {}
if 'logged_other_fluids' not in st.session_state: st.session_state.logged_other_fluids = []
if 'total_pure_water_ml' not in st.session_state: st.session_state.total_pure_water_ml = 0
if 'calculated_targets' not in st.session_state: st.session_state.calculated_targets = None
if 'tmb_formula' not in st.session_state: st.session_state.tmb_formula = "N/A"
if 'activity_factor' not in st.session_state: st.session_state.activity_factor = "N/A"
if 'bf_skinfold' not in st.session_state: st.session_state.bf_skinfold = None
if 'bf_circumference' not in st.session_state: st.session_state.bf_circumference = None
if 'bf_bmi_estimate' not in st.session_state: st.session_state.bf_bmi_estimate = None
if 'bf_method_choice' not in st.session_state: st.session_state.bf_method_choice = "Manual"
if 'food_search_term' not in st.session_state: st.session_state.food_search_term = ""
if 'other_fluid_search_term' not in st.session_state: st.session_state.other_fluid_search_term = ""

# --- Interface do Usuário (Streamlit) ---
# Código começa na coluna 0
st.title("Projeto Saúde Vida 360 - Calculadora Nutricional Esportiva")

# Código na coluna 0
if food_db.empty:
    st.error("Aplicação parada: banco de dados não carregado.")
    st.stop() # Para a execução

# --- Barra Lateral ---
# Código começa na coluna 0
with st.sidebar:
    # Código dentro do 'with' DEVE ser indentado
    st.header("👤 Seu Perfil")
    age = st.number_input("Idade", 10, 100, 30, 1)
    sex = st.radio("Sexo", ('Masculino', 'Feminino'), key='sex_radio')
    weight = st.number_input("Peso (kg)", 30.0, 250.0, 75.0, 0.5, "%.1f")
    height = st.number_input("Altura (cm)", 100.0, 250.0, 175.0, 0.5, "%.1f")
    bmi_value = calculate_bmi(weight, height)
    if bmi_value is not None:
        bmi_class = classify_bmi(bmi_value)
        st.metric(label="IMC", value=f"{bmi_value:.1f}", delta=bmi_class, delta_color="off")
    else:
        st.text("IMC: N/A")

    st.markdown("---") # Esta linha DEVE estar indentada como o resto do código dentro do 'with'
    st.header("💪 % Gordura Corporal")

    with st.expander("Dobras Cutâneas (J&P 3)"):
        # Código dentro do expander também indentado
        dobras_input = {}
        if sex == 'Masculino':
            dobras_input['peitoral'] = st.number_input("P", 1.0, step=0.1, format="%.1f", key='dc_peit', help="Dobra Peitoral (mm)")
            dobras_input['abdomen'] = st.number_input("Ab", 1.0, step=0.1, format="%.1f", key='dc_abd', help="Dobra Abdominal (mm)")
            dobras_input['coxa'] = st.number_input("Cx", 1.0, step=0.1, format="%.1f", key='dc_coxa_m', help="Dobra Coxa (mm)")
        else:
            dobras_input['triceps'] = st.number_input("Tr", 1.0, step=0.1, format="%.1f", key='dc_tric', help="Dobra Tricipital (mm)")
            dobras_input['suprailiaca'] = st.number_input("Si", 1.0, step=0.1, format="%.1f", key='dc_supra', help="Dobra Supra-ilíaca (mm)")
            dobras_input['coxa'] = st.number_input("Cx", 1.0, step=0.1, format="%.1f", key='dc_coxa_f', help="Dobra Coxa (mm)")
        if st.button("Calc (Dobras)", key='calc_bf_skinfold'):
            bf_result = calcular_bf_jp3(sex, age, dobras_input)
            st.session_state.bf_skinfold = bf_result
            # ... (feedback)
        if st.session_state.bf_skinfold is not None:
             st.write(f"**Res: {st.session_state.bf_skinfold:.1f}%**")

    with st.expander("Circunferências (US Navy)"):
        circ_neck = st.number_input("Pescoço (cm)", 10.0, 100.0, 38.0, 0.1, "%.1f", key='circ_neck')
        circ_waist = st.number_input("Cintura (cm)", 40.0, 200.0, 85.0, 0.1, "%.1f", key='circ_waist')
        circ_hip = None
        if sex == 'Feminino':
            circ_hip = st.number_input("Quadril (cm)", 40.0, 200.0, 95.0, 0.1, "%.1f", key='circ_hip')
        if st.button("Calc (Circunf.)", key='calc_bf_circ'):
            bf_result = calculate_bf_us_navy(sex, height, circ_neck, circ_waist, hip_cm=circ_hip)
            st.session_state.bf_circumference = bf_result
            # ... (feedback)
        if st.session_state.bf_circumference is not None:
            st.write(f"**Res: {st.session_state.bf_circumference:.1f}%**")

    with st.expander("Estimativa por IMC"):
        st.warning("❗ Estimativa")
        if bmi_value is not None:
            if st.button("Estim (IMC)", key='calc_bf_bmi'):
                bf_result = estimate_bf_from_bmi(bmi_value, age, sex)
                st.session_state.bf_bmi_estimate = bf_result
                # ... (feedback)
            if st.session_state.bf_bmi_estimate is not None:
                st.write(f"**Res: {st.session_state.bf_bmi_estimate:.1f}%**")
        else:
            st.info("IMC não calculado.")

    st.markdown("---")
    st.subheader("Usar qual % Gordura?")
    bf_options = ["Manual"]; bf_values = {"Manual": 0.0}
    if st.session_state.bf_skinfold is not None: opt = f"Dobras ({st.session_state.bf_skinfold:.1f}%)"; bf_options.append(opt); bf_values[opt] = st.session_state.bf_skinfold
    if st.session_state.bf_circumference is not None: opt = f"Circunf. ({st.session_state.bf_circumference:.1f}%)"; bf_options.append(opt); bf_values[opt] = st.session_state.bf_circumference
    if st.session_state.bf_bmi_estimate is not None: opt = f"Estimativa IMC ({st.session_state.bf_bmi_estimate:.1f}%)"; bf_options.append(opt); bf_values[opt] = st.session_state.bf_bmi_estimate
    fat_percentage_manual = st.number_input("% Gordura (Manual)", 0.0, 70.0, 0.0, 0.1, "%.1f", key='bf_manual'); bf_values["Manual"] = fat_percentage_manual if fat_percentage_manual > 0 else None
    current_choice = st.session_state.get('bf_method_choice', "Manual"); current_choice = current_choice if current_choice in bf_options else "Manual"; selected_bf_option = st.radio("Fonte:", options=bf_options, index=bf_options.index(current_choice), key='bf_choice_radio'); st.session_state.bf_method_choice = selected_bf_option
    fat_percentage_to_use = bf_values.get(selected_bf_option, None); fat_percentage_to_use = None if selected_bf_option == "Manual" and fat_percentage_to_use == 0.0 else fat_percentage_to_use
    if fat_percentage_to_use is not None: st.info(f"✅ Usando {fat_percentage_to_use:.1f}%")
    else: st.info(f"ℹ️ TMB por Mifflin")

    st.markdown("---")
    st.header("🏃 Nível de Atividade")
    activity_level_options = ['Sedentário (Pouco ou nenhum exercício)', 'Levemente Ativo (Exercício leve 1-3 dias/semana)', 'Moderadamente Ativo (Exercício moderado 3-5 dias/semana)', 'Muito Ativo (Exercício intenso 6-7 dias/semana)', 'Extremamente Ativo (Exercício muito intenso + trabalho físico)']
    activity_level = st.selectbox("Nível Atividade", activity_level_options, index=2)

    st.markdown("---")
    st.header("🎯 Suas Metas")
    protein_goal_g_kg = st.slider("Proteína (g/kg)", 1.0, 3.0, 1.8, 0.1, "%.1f")
    fat_goal_percentage = st.slider("Gordura (% GET)", 15.0, 40.0, 25.0, 1.0, "%.1f")

    st.markdown("---")
    calculate_button = st.button("Calcular Necessidades e Metas", type="primary", key='main_calc_button')

# --- Área Principal ---
# Código começa na coluna 0
if calculate_button:
    # Código dentro do if DEVE ser indentado
    st.session_state.calculated_targets = None
    lbm = calcular_lbm(weight, fat_percentage_to_use)
    tmb = calcular_tmb(weight, height, age, sex, lbm_kg=lbm)
    if tmb:
        get = calcular_get(tmb, activity_level)
        if get:
            macros = calcular_macros(get, weight, protein_goal_g_kg, fat_goal_percentage)
            if all(m is not None for m in macros):
                st.session_state.calculated_targets = macros
                st.success("Metas calculadas!")
                st.session_state.bf_skinfold = None
                st.session_state.bf_circumference = None
                st.session_state.bf_bmi_estimate = None

# Código começa na coluna 0
if st.session_state.calculated_targets:
    # Código dentro do if DEVE ser indentado
    kcal_target, prot_target, carb_target, fat_target = st.session_state.calculated_targets
    st.header("📊 Suas Necessidades Diárias Estimadas")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Calorias (GET)", f"{kcal_target:.0f} kcal")
    col2.metric("Proteínas", f"{prot_target:.1f} g")
    col3.metric("Carboidratos", f"{carb_target:.1f} g")
    col4.metric("Gorduras", f"{fat_target:.1f} g")
    details = []
    if 'tmb_formula' in st.session_state and st.session_state.tmb_formula != "N/A": details.append(f"TMB: {st.session_state.tmb_formula}")
    if 'activity_factor' in st.session_state and st.session_state.activity_factor != "N/A": details.append(f"Fator Ativ.: {st.session_state.activity_factor:.3f}")
    if details: st.caption(" | ".join(details))

    st.markdown("---")
    st.header("🍳 Registrar Alimentos")
    search_term = st.text_input("Buscar Alimento:", value=st.session_state.food_search_term, key="food_search")
    st.session_state.food_search_term = search_term
    if search_term: filtered_db = food_db[food_db['Nome_Alimento'].str.contains(search_term, case=False, na=False)]
    else: filtered_db = food_db
    col_food, col_qty, col_btn = st.columns([3, 1, 1])
    with col_food:
        food_options = filtered_db['Nome_Alimento'].tolist()
        if not food_options: st.warning(f"Nada encontrado para '{search_term}'."); food_options = food_db['Nome_Alimento'].tolist(); filtered_db = food_db
        selected_food_name = st.selectbox("Selecione na lista filtrada:", food_options, key="food_selector", index=0 if food_options else -1)
    with col_qty: quantity_grams = st.number_input("Quantidade (g)", 1, value=100, step=1, key="food_quantity")
    with col_btn: st.write(""); st.write(""); add_food_button = st.button("Adicionar Alim.", key="add_food")
    if add_food_button and selected_food_name and quantity_grams > 0:
        food_data_row = food_db[food_db['Nome_Alimento'] == selected_food_name]
        if not food_data_row.empty:
            food_data = food_data_row.iloc[0]; factor = quantity_grams / 100.0
            try:
                kcal = float(food_data['Energia_kcal_100g']) * factor; prot = float(food_data['Proteina_g_100g']) * factor; carb = float(food_data['Carboidrato_g_100g']) * factor; fat = float(food_data['Lipideos_g_100g']) * factor
                st.session_state.logged_foods.append({'Alimento': selected_food_name, 'Quantidade (g)': quantity_grams, 'Kcal': kcal, 'Proteína (g)': prot, 'Carbo (g)': carb, 'Gordura (g)': fat})
                st.success(f"{selected_food_name} ({quantity_grams}g) adicionado!"); st.session_state.food_search_term = ""
                st.rerun() # Corrigido
            except (ValueError, TypeError, KeyError) as e: st.error(f"Erro processar '{selected_food_name}': {e}.")
        else: st.error(f"Erro: '{selected_food_name}' não encontrado.")

    st.markdown("---")
    st.header("💊 Registrar Suplementos")
    all_supplements = {**PREDEFINED_SUPPLEMENTS, **st.session_state.custom_supplements}
    supplement_options = sorted(list(all_supplements.keys()))
    col_supp, col_dose, col_add_supp = st.columns([3, 1, 1])
    with col_supp: selected_supplement_name = st.selectbox("Selecione o Suplemento", supplement_options, key="supp_selector", index=0 if supplement_options else -1)
    with col_dose: supplement_dose_g = st.number_input("Dose (g)", min_value=0.1, value=5.0, step=0.1, format="%.1f", key="supp_dose")
    with col_add_supp: st.write(""); st.write(""); add_supp_button = st.button("Adicionar Suplem.", key="add_supp")
    if add_supp_button and selected_supplement_name and supplement_dose_g > 0:
        if selected_supplement_name in all_supplements:
            supp_data = all_supplements[selected_supplement_name]
            try:
                kcal = supp_data['kcal_g'] * supplement_dose_g; prot = supp_data['p_g'] * supplement_dose_g; carb = supp_data['c_g'] * supplement_dose_g; fat = supp_data['l_g'] * supplement_dose_g
                ca_mg = supp_data.get('ca_mg_g', 0.0) * supplement_dose_g; fe_mg = supp_data.get('fe_mg_g', 0.0) * supplement_dose_g
                st.session_state.logged_supplements.append({'Suplemento': selected_supplement_name, 'Dose (g)': supplement_dose_g, 'Kcal': kcal, 'Proteína (g)': prot, 'Carbo (g)': carb, 'Gordura (g)': fat, 'Cálcio (mg)': ca_mg, 'Ferro (mg)': fe_mg })
                st.success(f"{selected_supplement_name} ({supplement_dose_g}g) adicionado!")
            except KeyError as e: st.error(f"Dados incompletos para '{selected_supplement_name}': {e}")
            except Exception as e: st.error(f"Erro processar '{selected_supplement_name}': {e}")
        else: st.error(f"Suplemento '{selected_supplement_name}' não encontrado.")
    with st.expander("Adicionar Suplemento Customizado à Lista (Temporário)"):
        st.caption("Dados disponíveis apenas durante esta sessão.")
        custom_name = st.text_input("Nome Suplemento Customizado", key="custom_supp_name")
        col_cust1, col_cust2 = st.columns(2)
        with col_cust1:
             custom_kcal_100g = st.number_input("Kcal / 100g", 0.0, format="%.1f", key="custom_kcal"); custom_prot_100g = st.number_input("Proteína (g) / 100g", 0.0, format="%.1f", key="custom_prot"); custom_carb_100g = st.number_input("Carboidrato (g) / 100g", 0.0, format="%.1f", key="custom_carb"); custom_lip_100g = st.number_input("Lipídeos (g) / 100g", 0.0, format="%.1f", key="custom_lip")
        with col_cust2:
             custom_ca_100g = st.number_input("Cálcio (mg) / 100g", 0.0, format="%.1f", key="custom_ca")
             custom_fe_100g = st.number_input("Ferro (mg) / 100g", 0.0, format="%.1f", key="custom_fe")
        if st.button("Salvar Suplemento Customizado", key="save_custom_supp"):
            if custom_name and custom_name not in PREDEFINED_SUPPLEMENTS and custom_name not in st.session_state.custom_supplements:
                st.session_state.custom_supplements[custom_name] = {"kcal_g": custom_kcal_100g / 100.0, "p_g": custom_prot_100g / 100.0, "c_g": custom_carb_100g / 100.0, "l_g": custom_lip_100g / 100.0, "ca_mg_g": custom_ca_100g / 100.0, "fe_mg_g": custom_fe_100g / 100.0 }
                st.success(f"'{custom_name}' adicionado!");
                st.rerun() # Corrigido
            elif not custom_name: st.error("Insira um nome.")
            else: st.error(f"'{custom_name}' já existe.")

    st.markdown("---")
    st.header("💧 Registrar Líquidos")
    water_recommendation_ml = weight * 35
    st.info(f"Recomendação Hídrica Estimada: **{water_recommendation_ml:.0f} ml / dia**")
    col_water, col_add_water = st.columns([1,1])
    with col_water: pure_water_ml = st.number_input("Adicionar Água Pura (ml)", 50, value=250, step=50, key="pure_water_input")
    with col_add_water:
        st.write("");
        if st.button("Adicionar Água", key="add_water_button"):
            st.session_state.total_pure_water_ml += pure_water_ml; st.success(f"{pure_water_ml} ml de água adicionados!")
    st.subheader("Registrar Outras Bebidas (Usando Base de Alimentos)")
    other_fluid_search = st.text_input("Buscar Bebida:", value=st.session_state.other_fluid_search_term, key="other_fluid_search")
    st.session_state.other_fluid_search_term = other_fluid_search
    if other_fluid_search: filtered_fluid_db = food_db[food_db['Nome_Alimento'].str.contains(other_fluid_search, case=False, na=False)]
    else: filtered_fluid_db = food_db
    col_fluid, col_vol, col_add_fluid = st.columns([3, 1, 1])
    with col_fluid:
        fluid_options = filtered_fluid_db['Nome_Alimento'].tolist(); common_drinks_keywords = ['suco', 'refri', 'leite', 'agua de', 'cha ', 'café', 'bebida', 'isot', 'energetico']
        filtered_fluid_options = [f for f in fluid_options if any(keyword in f.lower() for keyword in common_drinks_keywords)]
        if not filtered_fluid_options and not other_fluid_search: filtered_fluid_options = fluid_options
        elif not filtered_fluid_options and other_fluid_search: st.warning(f"Nada para '{other_fluid_search}'. Mostrando lista geral."); filtered_fluid_options = fluid_options
        selected_fluid_name = st.selectbox("Selecione a Bebida:", filtered_fluid_options, key="other_fluid_selector", index=0 if filtered_fluid_options else -1)
    with col_vol: fluid_volume_ml = st.number_input("Volume (ml)", 50, value=200, step=10, key="other_fluid_volume")
    with col_add_fluid: st.write(""); st.write(""); add_fluid_button = st.button("Adicionar Bebida", key="add_fluid_button")
    if add_fluid_button and selected_fluid_name and fluid_volume_ml > 0:
        fluid_data_row = food_db[food_db['Nome_Alimento'] == selected_fluid_name]
        if not fluid_data_row.empty:
            fluid_data = fluid_data_row.iloc[0]; factor = fluid_volume_ml / 100.0
            try:
                kcal = float(fluid_data['Energia_kcal_100g']) * factor; prot = float(fluid_data['Proteina_g_100g']) * factor; carb = float(fluid_data['Carboidrato_g_100g']) * factor; fat = float(fluid_data['Lipideos_g_100g']) * factor
                st.session_state.logged_other_fluids.append({'Bebida': selected_fluid_name, 'Volume (ml)': fluid_volume_ml, 'Kcal': kcal, 'Proteína (g)': prot, 'Carbo (g)': carb, 'Gordura (g)': fat})
                st.success(f"{selected_fluid_name} ({fluid_volume_ml}ml) adicionado!"); st.session_state.other_fluid_search_term = ""
                st.rerun() # Corrigido
            except (ValueError, TypeError, KeyError) as e: st.error(f"Erro processar bebida '{selected_fluid_name}': {e}.")
        else: st.error(f"Erro: Bebida '{selected_fluid_name}' não encontrada.")

    st.markdown("---")
    st.header("📝 Resumo Geral do Dia")
    total_food_kcal = 0.0; total_food_prot = 0.0; total_food_carb = 0.0; total_food_fat = 0.0
    log_food_df = None
    if st.session_state.logged_foods:
        log_food_df = pd.DataFrame(st.session_state.logged_foods); total_food_kcal = log_food_df['Kcal'].sum(); total_food_prot = log_food_df['Proteína (g)'].sum(); total_food_carb = log_food_df['Carbo (g)'].sum(); total_food_fat = log_food_df['Gordura (g)'].sum()
    total_supp_kcal = 0.0; total_supp_prot = 0.0; total_supp_carb = 0.0; total_supp_fat = 0.0; total_supp_ca = 0.0; total_supp_fe = 0.0
    log_supp_df = None
    if st.session_state.logged_supplements:
        log_supp_df = pd.DataFrame(st.session_state.logged_supplements); total_supp_kcal = log_supp_df['Kcal'].sum(); total_supp_prot = log_supp_df['Proteína (g)'].sum(); total_supp_carb = log_supp_df['Carbo (g)'].sum(); total_supp_fat = log_supp_df['Gordura (g)'].sum(); total_supp_ca = log_supp_df['Cálcio (mg)'].sum(); total_supp_fe = log_supp_df['Ferro (mg)'].sum()
    total_fluid_kcal = 0.0; total_fluid_prot = 0.0; total_fluid_carb = 0.0; total_fluid_fat = 0.0
    log_fluid_df = None
    if st.session_state.logged_other_fluids:
        log_fluid_df = pd.DataFrame(st.session_state.logged_other_fluids); total_fluid_kcal = log_fluid_df['Kcal'].sum(); total_fluid_prot = log_fluid_df['Proteína (g)'].sum(); total_fluid_carb = log_fluid_df['Carbo (g)'].sum(); total_fluid_fat = log_fluid_df['Gordura (g)'].sum()
    total_kcal = total_food_kcal + total_supp_kcal + total_fluid_kcal; total_prot = total_food_prot + total_supp_prot + total_fluid_prot; total_carb = total_food_carb + total_supp_carb + total_fluid_carb; total_fat = total_food_fat + total_supp_fat + total_fluid_fat

    st.subheader("Alimentos Consumidos:")
    if log_food_df is None or log_food_df.empty: st.info("- Nenhum alimento adicionado.")
    else: display_food_df = log_food_df[['Alimento', 'Quantidade (g)', 'Kcal', 'Proteína (g)', 'Carbo (g)', 'Gordura (g)']]; st.dataframe(display_food_df.style.format("{:.1f}", subset=pd.IndexSlice[:, ['Kcal', 'Proteína (g)', 'Carbo (g)', 'Gordura (g)']], na_rep='-').format({'Quantidade (g)': '{:.0f}'}), height=min(200, len(log_food_df) * 38 + 40))
    st.subheader("Suplementos Consumidos:")
    if log_supp_df is None or log_supp_df.empty: st.info("- Nenhum suplemento adicionado.")
    else: display_supp_df = log_supp_df[['Suplemento', 'Dose (g)', 'Kcal', 'Proteína (g)', 'Carbo (g)', 'Gordura (g)', 'Cálcio (mg)', 'Ferro (mg)']]; st.dataframe(display_supp_df.style.format("{:.1f}", na_rep='-'), height=min(150, len(log_supp_df) * 38 + 40))
    st.subheader("Outras Bebidas Consumidas:")
    if log_fluid_df is None or log_fluid_df.empty: st.info("- Nenhuma outra bebida adicionada.")
    else: display_fluid_df = log_fluid_df[['Bebida', 'Volume (ml)', 'Kcal', 'Proteína (g)', 'Carbo (g)', 'Gordura (g)']]; st.dataframe(display_fluid_df.style.format("{:.1f}", subset=pd.IndexSlice[:, ['Kcal', 'Proteína (g)', 'Carbo (g)', 'Gordura (g)']], na_rep='-').format({'Volume (ml)': '{:.0f}'}), height=min(150, len(log_fluid_df) * 38 + 40))

    st.subheader("Totais Nutricionais (Alim+Sup+Beb) vs. Metas:")
    def display_progress(label, consumed, target):
        target_val = float(target) if target is not None else 0; consumed_val = float(consumed) if consumed is not None else 0
        if target_val > 0: progress = min(consumed_val / target_val, 1.0); delta = consumed_val - target_val; st.metric(label=label, value=f"{consumed_val:.1f} / {target_val:.1f}", delta=f"{delta:.1f} g" if label != "Calorias" else f"{delta:.0f} kcal", delta_color="off"); st.progress(progress)
        else: st.metric(label=label, value=f"{consumed_val:.1f} / {target_val:.1f}", delta="Meta inválida", delta_color="off"); st.progress(0)
    col_prog1, col_prog2 = st.columns(2)
    with col_prog1: display_progress("Calorias", total_kcal, kcal_target); display_progress("Proteínas", total_prot, prot_target)
    with col_prog2: display_progress("Carboidratos", total_carb, carb_target); display_progress("Gorduras", total_fat, fat_target)
    st.subheader("Resumo Hídrico e Micronutrientes (Suplem.):")
    total_other_fluid_ml = log_fluid_df['Volume (ml)'].sum() if log_fluid_df is not None and not log_fluid_df.empty else 0
    total_fluid_ml = st.session_state.total_pure_water_ml + total_other_fluid_ml
    water_recommendation_ml = weight * 35 # Recalcula aqui caso peso mude
    col_liq1, col_liq2, col_micro1, col_micro2 = st.columns(4)
    col_liq1.metric("Água Pura", f"{st.session_state.total_pure_water_ml:.0f} ml")
    col_liq2.metric("Total Líquidos", f"{total_fluid_ml:.0f} ml", delta=f"Meta: {water_recommendation_ml:.0f} ml", delta_color="off")
    col_micro1.metric("Cálcio (Suplem.)", f"{total_supp_ca:.1f} mg")
    col_micro2.metric("Ferro (Suplem.)", f"{total_supp_fe:.1f} mg")

    if st.button("Limpar TODOS os Logs (Alim, Suplem, Líquidos)"):
        st.session_state.logged_foods = []
        st.session_state.logged_supplements = []
        st.session_state.logged_other_fluids = []
        st.session_state.total_pure_water_ml = 0
        st.success("Todos os logs diários foram limpos!")
        st.rerun() # Corrigido

elif not calculate_button and not st.session_state.calculated_targets:
    st.info("📊 Preencha seus dados...")