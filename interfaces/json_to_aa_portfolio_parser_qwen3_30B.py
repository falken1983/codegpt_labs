import json
import os
import logging
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace
from xml.dom import minidom

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trade_parser.log'),
        logging.StreamHandler()
    ]
)

def excel_date_to_string(excel_date):
    """Convierte fecha Excel (OLE) a formato ddMMMyyyy"""
    try:
        # Fecha base de Excel (1900-01-01)
        base_date = datetime(1900, 1, 1)
        # Ajuste para fechas de Excel
        adjusted_date = base_date + timedelta(days=excel_date - 2)
        return adjusted_date.strftime("%d%b%Y")
    except Exception as e:
        logging.error(f"Error convirtiendo fecha Excel {excel_date}: {e}")
        return None

def get_observation_frequency(fdates):
    """Calcula la frecuencia de observación a partir de las fechas"""
    try:
        if len(fdates) < 2:
            return "1W"
        
        # Convertir fechas Excel a datetime
        dates = []
        for fdate in fdates[:2]:  # Solo necesitamos las dos primeras
            date_obj = excel_date_to_datetime(fdate)
            if date_obj:
                dates.append(date_obj)
        
        if len(dates) < 2:
            return "1W"
        
        # Calcular diferencia en semanas
        diff = (dates[1] - dates[0]).days
        weeks = diff // 7
        
        if weeks <= 0:
            return "1W"
            
        return f"{weeks}W"
    except Exception as e:
        logging.error(f"Error calculando frecuencia de observación: {e}")
        return "1W"

def excel_date_to_datetime(excel_date):
    """Convierte fecha Excel a datetime"""
    try:
        base_date = datetime(1900, 1, 1)
        adjusted_date = base_date + timedelta(days=excel_date - 2)
        return adjusted_date
    except Exception as e:
        logging.error(f"Error convirtiendo fecha Excel {excel_date}: {e}")
        return None

def parse_json_to_xml(json_data, filename):
    """Convierte un trade JSON a XML compatible con FIS AA"""
    try:
        # Extraer información clave del JSON
        trade_type = json_data.get("__type__")
        if trade_type != "Trade":
            logging.warning(f"El archivo {filename} no es un trade válido")
            return None
            
        # Extraer datos principales
        trade_nb = json_data.get("tradeNB", "")
        reference = str(trade_nb)[-8:] if len(str(trade_nb)) >= 8 else str(trade_nb).zfill(8)
        
        # Fecha de observación inicial y final
        fdates = json_data.get("FDATE", [])
        first_observation_date = None
        last_observation_date = None
        
        if fdates:
            first_observation_date = excel_date_to_string(fdates[0])
            last_observation_date = excel_date_to_string(fdates[-1])
        
        # Frecuencia de observación
        observation_frequency = get_observation_frequency(fdates)
        
        # Crear estructura XML
        deal = Element("Deal")
        deal.set("Object", "FxLeveragedAccumulator")
        deal.set("Reference", reference)
        deal.set("MtM", "<undefined>")
        deal.set("Tags", "<NONE>")
        
        # Añadir atributos principales
        attributes = {
            "Buy_Sell": json_data.get("Buy_Sell", ""),
            "Domestic_Currency": json_data.get("Domestic_Currency", ""),
            "Foreign_Currency": json_data.get("Foreign_Currency", ""),
            "Settlement_Date": excel_date_to_string(json_data.get("Settlement_Date", "")),
            "First_Observation_Date": first_observation_date,
            "Last_Observation_Date": last_observation_date,
            "Observation_Frequency": observation_frequency,
            "Expiry_Date": excel_date_to_string(json_data.get("Expiry_Date", "")),
            "Strike": str(json_data.get("Strike", "")),
            "Lower_Barrier": str(json_data.get("Lower_Barrier", "")),
            "Higher_Barrier": str(json_data.get("Higher_Barrier", "")),
            "Principal": str(json_data.get("Principal", "")),
            "Leveraged_Principal": str(json_data.get("Leveraged_Principal", "")),
            "Is_Fade_In": str(json_data.get("Is_Fade_In", "")).lower(),
            "Observation_Type": json_data.get("Observation_Type", ""),
            "Known_FX_Rates": "",
            "Accumulation_Currency": json_data.get("Accumulation_Currency", ""),
            "Observation_Schedule_Adjustment_Method": json_data.get("Observation_Schedule_Adjustment_Method", ""),
            "Calendars": json_data.get("Calendars", "")
        }
        
        # Añadir atributos al elemento Deal
        for key, value in attributes.items():
            if value is not None:
                deal.set(key, str(value))
        
        return deal
        
    except Exception as e:
        logging.error(f"Error procesando trade {filename}: {e}")
        return None

def create_portfolio_xml(deals):
    """Crea el XML completo de Portfolio con todos los trades"""
    try:
        # Registrar namespace para XML
        register_namespace('', 'http://www.fis.com/aa')
        
        portfolio = Element("Portfolio")
        portfolio.set("Name", "Converted Trades Portfolio")
        
        for deal in deals:
            if deal is not None:
                portfolio.append(deal)
        
        # Formatear el XML
        rough_string = tostring(portfolio, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
        
    except Exception as e:
        logging.error(f"Error creando Portfolio XML: {e}")
        return None

def process_json_folder(input_folder, output_file):
    """Procesa todos los archivos JSON en una carpeta y genera un Portfolio XML"""
    try:
        deals = []
        processed_count = 0
        error_count = 0
        
        # Recorrer todos los archivos en la carpeta
        for filename in os.listdir(input_folder):
            if filename.endswith('.json'):
                file_path = os.path.join(input_folder, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    
                    # Convertir a XML
                    deal_xml = parse_json_to_xml(json_data, filename)
                    if deal_xml is not None:
                        deals.append(deal_xml)
                        processed_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logging.error(f"Error procesando archivo {filename}: {e}")
                    error_count += 1
        
        # Generar el XML completo del Portfolio
        portfolio_xml = create_portfolio_xml(deals)
        
        if portfolio_xml:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(portfolio_xml)
            
            logging.info(f"Procesamiento completado:")
            logging.info(f"  - Trades procesados correctamente: {processed_count}")
            logging.info(f"  - Trades con errores: {error_count}")
            logging.info(f"  - Archivo de salida: {output_file}")
        else:
            logging.error("No se pudo generar el archivo XML del Portfolio")
            
    except Exception as e:
        logging.error(f"Error general en el procesamiento de la carpeta: {e}")

# Ejemplo de uso
if __name__ == "__main__":
    # Ruta a la carpeta con archivos JSON
    input_folder = "trades_json"
    output_file = "Portfolio.xml"
    
    # Crear carpeta si no existe
    os.makedirs(input_folder, exist_ok=True)
    
    # Procesar la carpeta
    process_json_folder(input_folder, output_file)
