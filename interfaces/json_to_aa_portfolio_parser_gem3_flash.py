import json
import os
import logging
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuración de Logging
logging.basicConfig(
    filename='trade_parser.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def excel_date_to_str(excel_date):
    """Convierte formato OLE (Excel) a string ddMMMyyyy."""
    if not excel_date or excel_date == 0:
        return ""
    # Excel considera 1900 como año bisiesto (error histórico), se ajusta con base 1899-12-30
    dt = datetime(1899, 12, 30) + timedelta(days=int(excel_date))
    return dt.strftime("%d%b%Y")

def infer_frequency(fdates):
    """Deduce la frecuencia de observación basada en los dos primeros elementos."""
    if len(fdates) < 2:
        return "1w"
    diff = fdates[1] - fdates[0]
    if diff == 7:
        return "1w"
    elif diff == 1:
        return "1d"
    elif 28 <= diff <= 31:
        return "1m"
    return "1w"  # Por defecto

def parse_known_fx_rates(strips):
    """Genera el string de Known_FX_Rates para fechas con valor fijado."""
    fdates = strips.get('FDATE', [])
    fvalues = strips.get('FVALUE', [])
    rates = []
    for d, v in zip(fdates, fvalues):
        if v > 0:
            rates.append(f"{excel_date_to_str(d)}={v}")
    return "\\".join(rates) + "\\" if rates else ""

def json_to_aa_xml_deal(json_data, filename):
    """Traduce un trade individual a formato de cadena XML <Deal>."""
    try:
        if json_data.get("__type__") != "Trade":
            return None

        # Extracción de Referencia (8 dígitos del nombre de archivo)
        # Ejemplo: trade_8093753_677.json -> 8093753
        ref = filename.split('_')[1] if '_' in filename else "00000000"
        
        flex = json_data['flexBlocks']['ACCUMKI']
        details = json_data['details']
        opt = details['optionDetails']
        strips = flex['strips']
        
        # Mapeo de campos
        fields = {
            "Object": "FxLeveragedAccumulator",
            "Reference": ref,
            "MtM": "<undefined>",
            "Tags": "<NONE>",
            "Buy_Sell": flex['BSCUR'].capitalize(),
            "Domestic_Currency": flex['SETCUR'],
            "Foreign_Currency": details['instruments']['name'].split('/')[0],
            "Settlement_Date": excel_date_to_str(flex['DELIV']),
            "First_Observation_Date": excel_date_to_str(strips['FDATE'][0]),
            "Last_Observation_Date": excel_date_to_str(strips['FDATE'][-1]),
            "Observation_Frequency": infer_frequency(strips['FDATE']),
            "Expiry_Date": excel_date_to_str(flex['EXP']),
            "Strike": flex['STRIKE'],
            "Lower_Barrier": flex['CLR'],
            "Higher_Barrier": flex['CHR'],
            "Principal": int(opt['notional'] / 2),
            "Leveraged_Principal": int(opt['notional']),
            "Is_Fade_In": "Yes" if flex['FADETY'] == "Fade In" else "No",
            "Observation_Type": "Above",
            "Known_FX_Rates": parse_known_fx_rates(strips),
            "Accumulation_Currency": flex['SETCUR'],
            "Observation_Schedule_Adjustment_Method": "Following",
            "Calendars": "TGT"
        }

        deal_content = ",".join([f"{k}={v}" for k, v in fields.items()])
        return deal_content

    except Exception as e:
        logging.error(f"Error procesando {filename}: {str(e)}")
        return None

def process_folder(folder_path, output_filename):
    """Recorre la carpeta, traduce trades y genera el Portfolio XML."""
    root = ET.Element("Deals")
    root.set("AnalyticsVersion", "213.200.11321.0")
    root.set("Reference", "New Portfolio:")
    root.set("Tag_Titles", "DIVEMU")

    processed_count = 0
    
    if not os.path.exists(folder_path):
        logging.error(f"La carpeta {folder_path} no existe.")
        return

    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            file_path = os.path.join(folder_path, file)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                deal_str = json_to_aa_xml_deal(data, file)
                
                if deal_str:
                    deal_elem = ET.SubElement(root, "Deal")
                    deal_elem.text = deal_str
                    processed_count += 1
                    logging.info(f"Trade {file} procesado correctamente.")
                else:
                    logging.warning(f"Archivo {file} no es un trade válido o faltan datos.")
            
            except Exception as e:
                logging.error(f"Error crítico leyendo {file}: {str(e)}")

    # Guardado del XML con formato legible
    xml_str = ET.tostring(root, encoding='utf-8')
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
    
    with open(output_filename, "w") as f:
        f.write(pretty_xml)
    
    print(f"Proceso finalizado. {processed_count} trades incluidos en {output_filename}")

# Ejemplo de uso
if __name__ == "__main__":
    # Asegúrate de que la ruta sea correcta según tu entorno
    process_folder('.', 'Portfolio_Final.xml')