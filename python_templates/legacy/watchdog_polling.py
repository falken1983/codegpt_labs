import sys
import time
import os
import logging
import smtplib
import subprocess
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Importamos PollingObserver para unidades de red
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

# --- CONFIGURACIÓN ---
# ¡IMPORTANTE! En Task Scheduler usa SIEMPRE rutas absolutas
WATCH_DIRECTORY = r"Z:\ruta\de\red\entrada_archivos" 
FILE_DATE_FORMAT = "%Y%m%d"
REQUIRED_FILE_COUNT = 4

# Rutas de tus scripts a ejecutar
PYTHON_EXE = sys.executable # Usa el mismo intérprete que está corriendo este script
SCRIPT_1_PATH = r"C:\Scripts\Procesos\proceso_etl_parte1.py"
SCRIPT_2_PATH = r"C:\Scripts\Procesos\proceso_generacion_informe.py"

# Configuración Correo Teams
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
SMTP_USER = "tu_usuario@empresa.com"
SMTP_PASSWORD = "tu_password"
TEAMS_CHANNEL_EMAIL = "tu-canal@amer.teams.ms"

# Logging
LOG_FILE = r"C:\Scripts\Logs\watchdog_log.txt"
logging.basicConfig(filename=LOG_FILE,
                    level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
# También imprimir en consola para debug
logging.getLogger().addHandler(logging.StreamHandler())

class FileAccumulatorHandler(FileSystemEventHandler):
    def __init__(self, target_date_str):
        self.target_date_str = target_date_str
        self.found_files = set()
        self.process_triggered = False

    def is_valid_file(self, filename):
        """Valida si el fichero cumple las condiciones."""
        return (self.target_date_str in filename 
                and not filename.startswith('.') 
                and not filename.endswith('.tmp')) # Evitar temporales de copia

    def on_created(self, event):
        if event.is_directory: return
        
        filename = os.path.basename(event.src_path)
        if self.is_valid_file(filename):
            logging.info(f"NUEVO fichero detectado en tiempo real: {filename}")
            self.found_files.add(filename)
            self.check_completeness()

    def check_completeness(self):
        if self.process_triggered: return

        current_count = len(self.found_files)
        logging.info(f"Estado actual: {current_count}/{REQUIRED_FILE_COUNT} ficheros.")

        if current_count >= REQUIRED_FILE_COUNT:
            self.process_triggered = True
            logging.info("!!! Objetivo alcanzado. Lanzando subprocesos... !!!")
            self.run_sequence()

    def run_sequence(self):
        start_time = datetime.now()
        error_ocurred = False
        error_msg = ""

        try:
            # --- PASO 1: PRIMER SCRIPT ---
            logging.info(f"Iniciando SCRIPT 1: {SCRIPT_1_PATH}")
            # check=True lanzará una excepción si el script devuelve un error (exit code != 0)
            subprocess.run([PYTHON_EXE, SCRIPT_1_PATH], check=True, capture_output=True, text=True)
            logging.info("SCRIPT 1 finalizado correctamente.")

            # --- PASO 2: SEGUNDO SCRIPT (Solo si el 1 va bien) ---
            logging.info(f"Iniciando SCRIPT 2: {SCRIPT_2_PATH}")
            subprocess.run([PYTHON_EXE, SCRIPT_2_PATH], check=True, capture_output=True, text=True)
            logging.info("SCRIPT 2 finalizado correctamente.")

        except subprocess.CalledProcessError as e:
            error_ocurred = True
            error_msg = f"Error ejecutando subproceso.\nComando: {e.cmd}\nSalida error: {e.stderr}"
            logging.error(error_msg)
        except Exception as e:
            error_ocurred = True
            error_msg = str(e)
            logging.error(f"Error inesperado: {e}")

        # Finalizar y notificar
        end_time = datetime.now()
        duration = end_time - start_time
        self.send_teams_notification(duration, list(self.found_files), error_ocurred, error_msg)
        
        # Salimos del Watchdog
        logging.info("Secuencia terminada. Cerrando Watchdog.")
        os._exit(0 if not error_ocurred else 1)

    def send_teams_notification(self, duration, file_list, error, error_details):
        status_emoji = "❌ FALLO" if error else "✅ ÉXITO"
        color = "#FF0000" if error else "#008000"
        
        files_str = "\n".join(['- ' + f for f in file_list])
        
        body = f"""
        Resultados de la Automatización: {status_emoji}
        ----------------------------------
        📅 Fecha: {self.target_date_str}
        ⏱️ Duración total: {duration}
        
        📂 Ficheros detectados:
        {files_str}
        
        """
        
        if error:
            body += f"\n🛑 DETALLES DEL ERROR:\n{error_details}"
        else:
            body += "\n🚀 Los dos scripts se ejecutaron secuencialmente sin errores."

        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = TEAMS_CHANNEL_EMAIL
        msg['Subject'] = f"{status_emoji} Proceso ETL y Reporte - {self.target_date_str}"
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, TEAMS_CHANNEL_EMAIL, msg.as_string())
            server.quit()
        except Exception as e:
            logging.error(f"Fallo al enviar mail a Teams: {e}")

def initial_scan(handler, directory):
    """Escanea lo que YA existe antes de empezar a vigilar."""
    logging.info("Realizando escaneo inicial de ficheros existentes...")
    try:
        files = os.listdir(directory)
        for f in files:
            if handler.is_valid_file(f):
                logging.info(f"Fichero PRE-EXISTENTE encontrado: {f}")
                handler.found_files.add(f)
        
        # Comprobar si ya tenemos los 4 antes de iniciar el loop
        handler.check_completeness()
    except Exception as e:
        logging.error(f"Error accediendo a la ruta de red: {e}")

if __name__ == "__main__":
    today_str = datetime.now().strftime(FILE_DATE_FORMAT)
    
    # Verificación de ruta (especial para unidades de red)
    if not os.path.exists(WATCH_DIRECTORY):
        logging.error(f"NO SE ACCEDE A LA RUTA: {WATCH_DIRECTORY}. Revisa la conexión de red.")
        sys.exit(1)

    handler = FileAccumulatorHandler(target_date_str=today_str)

    # 1. Escaneo inicial (por si los ficheros ya llegaron)
    initial_scan(handler, WATCH_DIRECTORY)

    # 2. Si el escaneo inicial ya disparó el proceso, el script morirá en os._exit(0) dentro de run_sequence.
    # Si llegamos aquí, faltan ficheros. Iniciamos vigilancia.
    
    # USAMOS PollingObserver PARA UNIDADES DE RED
    observer = PollingObserver(timeout=5) # Revisa cada 5 segundos
    observer.schedule(handler, WATCH_DIRECTORY, recursive=False)
    observer.start()
    
    logging.info(f"Vigilancia activa (Polling) en: {WATCH_DIRECTORY}")

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()