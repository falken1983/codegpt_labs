import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import os

def cargar_configuracion(archivo_config='config.json'):
    """
    Carga la configuración desde un archivo JSON.
    
    Args:
        archivo_config (str): Ruta al archivo de configuración JSON
        
    Returns:
        dict: Diccionario con la configuración
    """
    try:
        with open(archivo_config, 'r') as f:
            config = json.load(f)
        print(f"Configuración cargada desde {archivo_config}")
        return config
    except FileNotFoundError:
        print(f"Archivo de configuración {archivo_config} no encontrado. Usando configuración por defecto.")
        return {
            "criptomonedas": ["BTC-EUR", "ETH-EUR", "XRP-EUR", "LTC-EUR", "ADA-EUR"],
            "periodo_años": 5,
            "directorio_salida": "./datos_cripto",
            "guardar_csv": True
        }
    except json.JSONDecodeError:
        print(f"Error al decodificar el archivo JSON {archivo_config}. Usando configuración por defecto.")
        return {
            "criptomonedas": ["BTC-EUR", "ETH-EUR", "XRP-EUR", "LTC-EUR", "ADA-EUR"],
            "periodo_años": 5,
            "directorio_salida": "./datos_cripto",
            "guardar_csv": True
        }

def descargar_datos_cripto(simbolos, periodo_años=5):
    """
    Descarga datos históricos de criptomonedas.
    
    Args:
        simbolos (list): Lista de símbolos de criptomonedas (ej. ['BTC-EUR', 'ETH-EUR'])
        periodo_años (int): Número de años de datos históricos a descargar
        
    Returns:
        DataFrame: DataFrame con los precios de cierre de las criptomonedas
    """
    # Calcular la fecha de inicio (hace X años desde hoy)
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=periodo_años*365)
    
    # Convertir fechas a formato string YYYY-MM-DD
    fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
    fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
    
    print(f"Descargando datos desde {fecha_inicio_str} hasta {fecha_fin_str}...")
    
    # Crear un DataFrame vacío para almacenar los precios de cierre
    df_precios = pd.DataFrame()
    
    # Descargar datos para cada símbolo
    simbolos_exitosos = []
    simbolos_fallidos = []
    
    for simbolo in simbolos:
        try:
            data = yf.download(simbolo, start=fecha_inicio_str, end=fecha_fin_str)
            if not data.empty:
                df_precios[simbolo] = data['Close']
                print(f"Datos descargados para {simbolo}: {len(data)} registros")
                simbolos_exitosos.append(simbolo)
            else:
                print(f"No se encontraron datos para {simbolo}")
                simbolos_fallidos.append(simbolo)
        except Exception as e:
            print(f"Error al descargar datos para {simbolo}: {e}")
            simbolos_fallidos.append(simbolo)
    
    print(f"\nResumen de descarga:")
    print(f"Símbolos descargados exitosamente: {len(simbolos_exitosos)}/{len(simbolos)}")
    if simbolos_fallidos:
        print(f"Símbolos sin datos: {', '.join(simbolos_fallidos)}")
    
    return df_precios

def calcular_indicadores_tecnicos(df):
    """
    Calcula indicadores técnicos comunes para cada criptomoneda.
    
    Args:
        df (DataFrame): DataFrame con precios de cierre
        
    Returns:
        dict: Diccionario con DataFrames de indicadores para cada criptomoneda
    """
    indicadores = {}
    
    for columna in df.columns:
        precios = df[columna].dropna()
        
        if len(precios) == 0:
            print(f"No hay datos suficientes para {columna}")
            continue
            
        # Crear DataFrame para almacenar los indicadores
        df_ind = pd.DataFrame(index=precios.index)
        df_ind['Precio'] = precios
        
        # 1. Medias Móviles (SMA)
        df_ind['SMA_7'] = precios.rolling(window=7).mean()
        df_ind['SMA_20'] = precios.rolling(window=20).mean()
        df_ind['SMA_50'] = precios.rolling(window=50).mean()
        df_ind['SMA_200'] = precios.rolling(window=200).mean()
        
        # 2. Media Móvil Exponencial (EMA)
        df_ind['EMA_12'] = precios.ewm(span=12, adjust=False).mean()
        df_ind['EMA_26'] = precios.ewm(span=26, adjust=False).mean()
        
        # 3. MACD (Moving Average Convergence Divergence)
        df_ind['MACD'] = df_ind['EMA_12'] - df_ind['EMA_26']
        df_ind['MACD_Signal'] = df_ind['MACD'].ewm(span=9, adjust=False).mean()
        df_ind['MACD_Hist'] = df_ind['MACD'] - df_ind['MACD_Signal']
        
        # 4. RSI (Relative Strength Index)
        delta = precios.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df_ind['RSI_14'] = 100 - (100 / (1 + rs))
        
        # 5. Bandas de Bollinger (20 períodos, 2 desviaciones estándar)
        df_ind['BB_Middle'] = precios.rolling(window=20).mean()
        std_dev = precios.rolling(window=20).std()
        df_ind['BB_Upper'] = df_ind['BB_Middle'] + (std_dev * 2)
        df_ind['BB_Lower'] = df_ind['BB_Middle'] - (std_dev * 2)
        
        # 6. Momentum (14 períodos)
        df_ind['Momentum_14'] = precios / precios.shift(14) * 100
        
        # 7. Rate of Change (ROC)
        df_ind['ROC_14'] = ((precios / precios.shift(14)) - 1) * 100
        
        # 8. Stochastic Oscillator
        low_14 = precios.rolling(window=14).min()
        high_14 = precios.rolling(window=14).max()
        df_ind['Stoch_K'] = 100 * ((precios - low_14) / (high_14 - low_14))
        df_ind['Stoch_D'] = df_ind['Stoch_K'].rolling(window=3).mean()
        
        # 9. Average True Range (ATR)
        # Para ATR necesitaríamos datos de High, Low, Close, pero solo tenemos Close
        # Así que calculamos una versión simplificada basada solo en Close
        df_ind['ATR_14'] = precios.rolling(window=14).std()
        
        # 10. Variación porcentual diaria
        df_ind['Var_Pct_Diaria'] = precios.pct_change() * 100
        
        # 11. Volatilidad (desviación estándar de rendimientos en 30 días)
        df_ind['Volatilidad_30'] = df_ind['Var_Pct_Diaria'].rolling(window=30).std()
        
        indicadores[columna] = df_ind
        
    return indicadores

def guardar_resultados(indicadores, directorio_salida):
    """
    Guarda los resultados en archivos CSV.
    
    Args:
        indicadores (dict): Diccionario con DataFrames de indicadores
        directorio_salida (str): Directorio donde guardar los archivos
    """
    # Crear directorio si no existe
    if not os.path.exists(directorio_salida):
        os.makedirs(directorio_salida)
        print(f"Directorio creado: {directorio_salida}")
    
    # Guardar cada DataFrame en un archivo CSV
    for simbolo, df in indicadores.items():
        # Reemplazar caracteres no válidos para nombres de archivo
        nombre_archivo = simbolo.replace('-', '_').replace('/', '_')
        ruta_archivo = os.path.join(directorio_salida, f"{nombre_archivo}_indicadores.csv")
        df.to_csv(ruta_archivo)
        print(f"Datos guardados en {ruta_archivo}")

def main():
    # Cargar configuración
    config = cargar_configuracion()
    
    # Obtener parámetros de la configuración
    criptomonedas = config.get("criptomonedas", ["BTC-EUR", "ETH-EUR"])
    periodo_años = config.get("periodo_años", 5)
    directorio_salida = config.get("directorio_salida", "./datos_cripto")
    guardar_csv = config.get("guardar_csv", True)
    
    print(f"Analizando {len(criptomonedas)} criptomonedas: {', '.join(criptomonedas)}")
    print(f"Período de análisis: {periodo_años} años")
    
    # Descargar datos históricos
    df_precios = descargar_datos_cripto(criptomonedas, periodo_años=periodo_años)
    
    # Verificar que se descargaron datos
    if df_precios.empty:
        print("No se pudieron descargar datos. Verifique su conexión a internet o los símbolos utilizados.")
        return
    
    # Calcular indicadores técnicos
    indicadores = calcular_indicadores_tecnicos(df_precios)
    
    # Mostrar información sobre los datos descargados
    print("\nInformación sobre los datos descargados:")
    print(f"Período: {df_precios.index[0].strftime('%Y-%m-%d')} a {df_precios.index[-1].strftime('%Y-%m-%d')}")
    print(f"Número de días: {len(df_precios)}")
    print(f"Criptomonedas con datos: {', '.join(df_precios.columns)}")
    
    # Guardar resultados si está configurado
    if guardar_csv:
        guardar_resultados(indicadores, directorio_salida)
    
    return df_precios, indicadores

if __name__ == "__main__":
    df_precios, indicadores = main()