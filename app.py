import streamlit as st
import CoolProp.CoolProp as CP

# --- Función para calcular eficiencia a partir de potencia ---

def calculate_isentropic_efficiency_and_capacity(P1_bar, T1_C, P2_bar, W_in_kW, mass_flow_kg_s):
    """
    Calcula la eficiencia isentrópica, la capacidad de refrigeración y la temperatura de descarga real,
    usando la potencia de entrada y el flujo másico.
    
    Argumentos:
    P1_bar (float): Presión de succión en bares.
    T1_C (float): Temperatura de succión en grados Celsius.
    P2_bar (float): Presión de descarga en bares.
    W_in_kW (float): Potencia de entrada al compresor en kilovatios (kW).
    mass_flow_kg_s (float): Flujo másico de refrigerante en kg/s.

    Retorna:
    tuple: (Eficiencia isentrópica en porcentaje, Capacidad de refrigeración en kW,
            h1, h2s, work_actual, T2s_C, T2a_C_calculated, Efecto Refrigerante en kJ/kg)
    """
    
    # Convertir unidades a SI (CoolProp usa Pa y Kelvin)
    P1_Pa = P1_bar * 100000  # bares a Pascales
    T1_K = T1_C + 273.15     # Celsius a Kelvin
    P2_Pa = P2_bar * 100000  # bares a Pascales
    W_in_W = W_in_kW * 1000  # kW a Watts

    refrigerant = 'Ammonia' # NH3

    try:
        # 1. Estado de Succión (Entrada al compresor)
        h1 = CP.PropsSI('H', 'P', P1_Pa, 'T', T1_K, refrigerant) # Entalpía de succión (J/kg)
        s1 = CP.PropsSI('S', 'P', P1_Pa, 'T', T1_K, refrigerant) # Entropía de succión (J/kg.K)

        # 2. Estado de Descarga Isentrópica (Ideal)
        h2s = CP.PropsSI('H', 'P', P2_Pa, 'S', s1, refrigerant) # Entalpía de descarga isentrópica (J/kg)
        T2s_K = CP.PropsSI('T', 'P', P2_Pa, 'S', s1, refrigerant) # Temperatura de descarga isentrópica (K)

        # Cálculo del trabajo isentrópico
        work_isentropic = h2s - h1

        # Cálculo del trabajo real a partir de la potencia de entrada y el flujo másico
        if mass_flow_kg_s <= 0:
            st.error("Error: El flujo másico debe ser un valor positivo para el cálculo del trabajo real y capacidad.")
            return None, None, None, None, None, None, None, None
        
        work_actual = W_in_W / mass_flow_kg_s # Trabajo real en J/kg

        if work_actual <= 0:
            st.error("Error: El trabajo real de compresión es cero o negativo, lo que no es posible.")
            return None, None, None, None, None, None, None, None

        # Cálculo de la entalpía de descarga real a partir del trabajo real
        h2a_calculated = h1 + work_actual
        T2a_K_calculated = CP.PropsSI('T', 'P', P2_Pa, 'H', h2a_calculated, refrigerant)
        T2a_C_calculated = T2a_K_calculated - 273.15

        # Cálculo de la eficiencia isentrópica
        isentropic_efficiency = (work_isentropic / work_actual) * 100
        
        # 3. Cálculo de la Capacidad de Refrigeración
        # Para estimar la capacidad, necesitamos la entalpía del líquido a la salida del condensador.
        # Usaremos la presión de descarga (P2) como presión de condensación.
        h_liquid_condenser = CP.PropsSI('H', 'P', P2_Pa, 'Q', 0, refrigerant) # Entalpía de líquido saturado
        
        # Efecto Refrigerante (RE) = Entalpía de succión (vapor) - Entalpía del líquido a la entrada de la válvula (después del condensador)
        refrigerating_effect = h1 - h_liquid_condenser
        refrigerating_effect_kJ_kg = refrigerating_effect / 1000 # Convertir a kJ/kg
        
        capacity_kW = (mass_flow_kg_s * refrigerating_effect) / 1000 # Convertir a kW

        return isentropic_efficiency, capacity_kW, h1, h2s, work_actual, T2s_K - 273.15, T2a_C_calculated, refrigerating_effect_kJ_kg

    except ValueError as e:
        st.error(f"Error en CoolProp: {e}. Asegúrate de que las condiciones de entrada sean válidas para el refrigerante (ej. no en la región de dos fases para estados de gas).")
        return None, None, None, None, None, None, None, None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado: {e}")
        return None, None, None, None, None, None, None, None


# --- Función para calcular potencia a partir de eficiencia ---

def calculate_power_from_efficiency(P1_bar, T1_C, P2_bar, isentropic_efficiency_percent, mass_flow_kg_s):
    """
    Calcula la potencia consumida, capacidad de refrigeración y temperatura de descarga real,
    usando la eficiencia isentrópica y el flujo másico.
    
    Argumentos:
    P1_bar (float): Presión de succión en bares.
    T1_C (float): Temperatura de succión en grados Celsius.
    P2_bar (float): Presión de descarga en bares.
    isentropic_efficiency_percent (float): Eficiencia isentrópica en porcentaje.
    mass_flow_kg_s (float): Flujo másico de refrigerante en kg/s.

    Retorna:
    tuple: (Potencia consumida en kW, Capacidad de refrigeración en kW,
            h1, h2s, work_actual, T2s_C, T2a_C_calculated, Efecto Refrigerante en kJ/kg, work_isentropic)
    """
    
    # Convertir unidades a SI (CoolProp usa Pa y Kelvin)
    P1_Pa = P1_bar * 100000  # bares a Pascales
    T1_K = T1_C + 273.15     # Celsius a Kelvin
    P2_Pa = P2_bar * 100000  # bares a Pascales
    
    refrigerant = 'Ammonia' # NH3

    try:
        # 1. Estado de Succión (Entrada al compresor)
        h1 = CP.PropsSI('H', 'P', P1_Pa, 'T', T1_K, refrigerant) # Entalpía de succión (J/kg)
        s1 = CP.PropsSI('S', 'P', P1_Pa, 'T', T1_K, refrigerant) # Entropía de succión (J/kg.K)

        # 2. Estado de Descarga Isentrópica (Ideal)
        h2s = CP.PropsSI('H', 'P', P2_Pa, 'S', s1, refrigerant) # Entalpía de descarga isentrópica (J/kg)
        T2s_K = CP.PropsSI('T', 'P', P2_Pa, 'S', s1, refrigerant) # Temperatura de descarga isentrópica (K)

        # Cálculo del trabajo isentrópico
        work_isentropic = h2s - h1

        if mass_flow_kg_s <= 0:
            st.error("Error: El flujo másico debe ser un valor positivo.")
            return None, None, None, None, None, None, None, None, None
            
        if isentropic_efficiency_percent <= 0 or isentropic_efficiency_percent > 100:
            st.error("Error: La eficiencia isentrópica debe estar entre 0 y 100%.")
            return None, None, None, None, None, None, None, None, None

        # Cálculo del trabajo real a partir de la eficiencia isentrópica
        isentropic_efficiency_decimal = isentropic_efficiency_percent / 100
        work_actual = work_isentropic / isentropic_efficiency_decimal # Trabajo real en J/kg

        # Cálculo de la potencia consumida
        W_consumed_W = work_actual * mass_flow_kg_s # Potencia en Watts
        W_consumed_kW = W_consumed_W / 1000 # Convertir a kW

        # Cálculo de la entalpía de descarga real a partir del trabajo real
        h2a_calculated = h1 + work_actual
        T2a_K_calculated = CP.PropsSI('T', 'P', P2_Pa, 'H', h2a_calculated, refrigerant)
        T2a_C_calculated = T2a_K_calculated - 273.15
        
        # 3. Cálculo de la Capacidad de Refrigeración
        h_liquid_condenser = CP.PropsSI('H', 'P', P2_Pa, 'Q', 0, refrigerant) # Entalpía de líquido saturado
        
        # Efecto Refrigerante (RE)
        refrigerating_effect = h1 - h_liquid_condenser
        refrigerating_effect_kJ_kg = refrigerating_effect / 1000 # Convertir a kJ/kg
        
        capacity_kW = (mass_flow_kg_s * refrigerating_effect) / 1000 # Convertir a kW

        return W_consumed_kW, capacity_kW, h1, h2s, work_actual, T2s_K - 273.15, T2a_C_calculated, refrigerating_effect_kJ_kg, work_isentropic

    except ValueError as e:
        st.error(f"Error en CoolProp: {e}. Asegúrate de que las condiciones de entrada sean válidas para el refrigerante.")
        return None, None, None, None, None, None, None, None, None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado: {e}")
        return None, None, None, None, None, None, None, None, None


# --- Configuración y UI de Streamlit ---

# Configuración inicial de la página
st.set_page_config(
    page_title="Calculadora de Compresores NH3",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("❄️ Calculadora de Compresores de Amoníaco (NH3)")

st.write("Esta herramienta permite realizar **dos tipos de cálculos** para compresores de Amoníaco:")
st.write("🔹 **Modo 1:** Calcular eficiencia isentrópica a partir de la potencia consumida")
st.write("🔹 **Modo 2:** Calcular potencia consumida a partir de la eficiencia isentrópica")

# --- Selector de modo de cálculo ---
calculation_mode = st.selectbox(
    "Selecciona el tipo de cálculo:",
    ["Calcular Eficiencia (desde Potencia)", "Calcular Potencia (desde Eficiencia)"],
    index=0
)

# --- Parámetros comunes ---
st.sidebar.header("Parámetros Comunes")

P1_bar = st.sidebar.number_input("Presión de succión (bar):", min_value=0.1, value=2.0, step=0.1, format="%.1f")
T1_C = st.sidebar.number_input("Temperatura de succión (°C):", value=-10.0, step=0.1, format="%.1f")
P2_bar = st.sidebar.number_input("Presión de descarga (bar):", min_value=P1_bar + 0.1, value=12.0, step=0.1, format="%.1f")
mass_flow_kg_s = st.sidebar.number_input("Flujo másico de NH3 (kg/s):", min_value=0.001, value=0.1, step=0.001, format="%.3f")

# --- Parámetros específicos según el modo ---
st.sidebar.header("Parámetros Específicos")

if calculation_mode == "Calcular Eficiencia (desde Potencia)":
    W_in_kW = st.sidebar.number_input("Potencia de entrada al compresor (kW):", min_value=0.1, value=45.0, step=0.1, format="%.1f")
    
    # Botón para cálculo de eficiencia
    if st.sidebar.button("Calcular Eficiencia"):
        isentropic_efficiency, capacity_kW, h1_val, h2s_val, work_actual_val, T2s_C_val, T2a_C_calculated_val, re_val = \
            calculate_isentropic_efficiency_and_capacity(P1_bar, T1_C, P2_bar, W_in_kW, mass_flow_kg_s)

        if isentropic_efficiency is not None:
            st.subheader("📊 Resultados del Cálculo - Eficiencia")
            
            # Mostrar métricas clave
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Eficiencia Isentrópica", value=f"{isentropic_efficiency:.2f} %")
            with col2:
                st.metric(label="Capacidad de Refrigeración", value=f"{capacity_kW:.2f} kW")
            with col3:
                st.metric(label="Temperatura Descarga Real", value=f"{T2a_C_calculated_val:.2f} °C")

            st.write("---")
            st.subheader("🔍 Detalles del Proceso Termodinámico")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Entalpía de Succión (h1):** {h1_val/1000:.2f} kJ/kg")
                st.write(f"**Entalpía de Descarga Isentrópica (h2s):** {h2s_val/1000:.2f} kJ/kg")
                st.write(f"**Temperatura de Descarga Isentrópica (T2s):** {T2s_C_val:.2f} °C")
            with col2:
                st.write(f"**Trabajo Isentrópico (h2s - h1):** {(h2s_val - h1_val)/1000:.2f} kJ/kg")
                st.write(f"**Trabajo Real (W_in / ṁ):** {work_actual_val/1000:.2f} kJ/kg")
                st.write(f"**Efecto Refrigerante:** {re_val:.2f} kJ/kg")

else:  # Calcular Potencia (desde Eficiencia)
    isentropic_efficiency_input = st.sidebar.number_input("Eficiencia isentrópica (%):", min_value=10.0, max_value=100.0, value=80.0, step=0.1, format="%.1f")
    
    # Botón para cálculo de potencia
    if st.sidebar.button("Calcular Potencia"):
        W_consumed_kW, capacity_kW, h1_val, h2s_val, work_actual_val, T2s_C_val, T2a_C_calculated_val, re_val, work_isentropic_val = \
            calculate_power_from_efficiency(P1_bar, T1_C, P2_bar, isentropic_efficiency_input, mass_flow_kg_s)

        if W_consumed_kW is not None:
            st.subheader("⚡ Resultados del Cálculo - Potencia")
            
            # Mostrar métricas clave
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Potencia Consumida", value=f"{W_consumed_kW:.2f} kW")
            with col2:
                st.metric(label="Capacidad de Refrigeración", value=f"{capacity_kW:.2f} kW")
            with col3:
                st.metric(label="Temperatura Descarga Real", value=f"{T2a_C_calculated_val:.2f} °C")

            st.write("---")
            st.subheader("🔍 Detalles del Proceso Termodinámico")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Entalpía de Succión (h1):** {h1_val/1000:.2f} kJ/kg")
                st.write(f"**Entalpía de Descarga Isentrópica (h2s):** {h2s_val/1000:.2f} kJ/kg")
                st.write(f"**Temperatura de Descarga Isentrópica (T2s):** {T2s_C_val:.2f} °C")
                st.write(f"**Eficiencia Utilizada:** {isentropic_efficiency_input:.1f} %")
            with col2:
                st.write(f"**Trabajo Isentrópico (h2s - h1):** {work_isentropic_val/1000:.2f} kJ/kg")
                st.write(f"**Trabajo Real Calculado:** {work_actual_val/1000:.2f} kJ/kg")
                st.write(f"**Efecto Refrigerante:** {re_val:.2f} kJ/kg")
                st.write(f"**COP (Capacidad/Potencia):** {capacity_kW/W_consumed_kW:.2f}")

# --- Información adicional ---
st.write("---")
st.info("💡 **Nota Importante:** La temperatura de descarga real calculada representa la temperatura del refrigerante al salir del compresor. En compresores de tornillo con inyección de aceite, la temperatura real medida puede ser menor debido al enfriamiento por aceite.")

with st.expander("ℹ️ Información sobre los cálculos"):
    st.write("""
    **Modo 1 - Calcular Eficiencia:**
    - Utiliza la potencia de entrada medida para determinar la eficiencia real del compresor
    - Útil para evaluar el rendimiento de un compresor existente
    
    **Modo 2 - Calcular Potencia:**
    - Utiliza una eficiencia conocida o esperada para predecir el consumo de potencia
    - Útil para dimensionamiento y selección de compresores
    
    **Fórmulas clave:**
    - Eficiencia isentrópica = (Trabajo isentrópico / Trabajo real) × 100%
    - Trabajo real = Potencia de entrada / Flujo másico
    - Capacidad = Flujo másico × Efecto refrigerante
    """)

st.write("---")
st.write("🔧 Desarrollado por Ariel Cuevas - Reficiencia SPA")