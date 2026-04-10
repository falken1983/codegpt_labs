import yaml
import subprocess
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from pathlib import Path
from datetime import datetime

def load_config(config_path):
    """Carga la configuración desde archivo YAML"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Valores por defecto
        config.setdefault('resource_config', {}).setdefault('cores_to_use', os.cpu_count())
        config.setdefault('log_config', {}).setdefault('log_file', 'orchestrator.log')
        config.setdefault('log_config', {}).setdefault('log_level', 'INFO')
        
        return config
    except Exception as e:
        logging.critical(f"Configuration load error: {str(e)}")
        raise

def setup_logging(log_config):
    """Configura el sistema de logging unificado"""
    log_file = Path(log_config['log_file']).resolve()
    log_level = getattr(logging, log_config['log_level'].upper())
    
    # Formateador con timestamp
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Manejador para archivo
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # Manejador para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configurar logger principal
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info(f"Logging system initialized. Log file: {log_file}")
    return logger

def run_simulation(script_path, target_directory):
    """Ejecuta el script de cálculo para un directorio específico"""
    try:
        result = subprocess.run(
            ["python", script_path, target_directory],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return (target_directory, True, result.stdout)
    except subprocess.CalledProcessError as e:
        return (target_directory, False, e.stderr)
    except Exception as e:
        return (target_directory, False, str(e))

def main():
    try:
        # Cargar configuración
        config = load_config("orchestrator_config.yaml")
        logger = setup_logging(config['log_config'])
        
        # Parámetros de ejecución
        directories = config['directories_to_process']
        calculation_script = config['calculation_script']
        cores = config['resource_config']['cores_to_use']
        
        logger.info(f"Starting orchestrator using {cores} CPU cores")
        logger.info(f"Directories to process: {', '.join(directories)}")
        
        # Pool de procesos
        with ProcessPoolExecutor(max_workers=cores) as executor:
            # Mapear futuros
            futures = {executor.submit(run_simulation, calculation_script, dir): dir for dir in directories}
            
            # Procesar resultados conforme van completando
            for future in as_completed(futures):
                original_dir = futures[future]
                try:
                    processed_dir, success, output = future.result()
                    if success:
                        logger.info(f"Successful processing: {processed_dir}")
                        logger.debug(f"{processed_dir} output:\n{output.strip()}")
                    else:
                        logger.error(f"Error in {processed_dir}\n{output.strip()}")
                except Exception as e:
                    logger.error(f"Unhandled exception in {original_dir}: {str(e)}")
        
        logger.info("All directories processed successfully")
    
    except Exception as e:
        logging.critical(f"Fatal orchestrator error: {str(e)}")
        raise

if __name__ == "__main__":
    main()