import os
from datetime import datetime
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Monitor de Archivos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicar estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .file-container {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #4CAF50;
    }
    .file-name {
        font-weight: bold;
        color: #666;
        font-size: 1.1rem;
    }
    .file-time {
        color: #666;
        font-size: 0.9rem;
    }
    
    /* Barra de progreso personalizada */
    .custom-progress-container {
        width: 100%;
        background-color: #e0e0e0;
        border-radius: 4px;
        margin: 10px 0;
        overflow: hidden;
    }
    .custom-progress-bar {
        height: 20px;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    .progress-complete {
        background-color: #4CAF50;
    }
    .progress-incomplete {
        background-color: #FFC107;
    }
</style>
""", unsafe_allow_html=True)

# Definir rutas predefinidas con sus etiquetas
RUTAS_PREDEFINIDAS = {
    "HOME": os.path.expanduser("~"),  # Ruta home del usuario actual
    "ROOT": "/",                      # Directorio raíz
    "Documentos": os.path.expanduser("~/Documents"),  # Ejemplo adicional
    "Descargas": os.path.expanduser("~/Downloads")    # Otro ejemplo
}

def monitorizar_directorio(directorio):
    """Monitoriza un directorio para archivos .txt generados hoy."""
    current_files = []
    today_date = datetime.now().date()
    
    try:
        for filename in os.listdir(directorio):
            filepath = os.path.join(directorio, filename)
            if os.path.isfile(filepath) and os.path.splitext(filename)[1].lower() == '.txt':
                # Obtener fecha de modificación
                modify_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if modify_time.date() == today_date:
                    file_size = os.path.getsize(filepath)
                    # Obtener nombre sin extensión
                    name_without_ext = os.path.splitext(filename)[0]
                    current_files.append({
                        'Nombre': name_without_ext,
                        'NombreCompleto': filename,
                        'Tamaño': file_size,
                        'Hora': modify_time.strftime('%H:%M:%S')
                    })
    except PermissionError:
        st.error(f"No tienes permisos para acceder al directorio {directorio}")
        return
    
    # Mostrar título y descripción en el panel principal
    st.markdown('<div class="main-header">Monitor de Archivos .txt</div>', unsafe_allow_html=True)
    
    # Fecha actual en el subheader
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    st.markdown(f'<div class="sub-header">Esta aplicación monitoriza archivos .txt generados hoy ({fecha_actual}) en el directorio seleccionado.</div>', unsafe_allow_html=True)
    
    st.write(f"📁 **Directorio actual:** {directorio}")
    
    # Verificar si hay archivos .txt
    if not current_files:
        st.info("No se han encontrado archivos .txt generados hoy en este directorio.")
    else:
        st.write(f"📊 **Archivos encontrados:** {len(current_files)}")
        
        # Mostrar archivos encontrados
        for file in current_files:
            with st.container():
                st.markdown(f"""
                <div class="file-container">
                    <div class="file-name">{file['Nombre']}</div>
                    <div class="file-time">Hora: {file['Hora']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Determinar el progreso y clase CSS
                if file['Tamaño'] > 0:
                    progress_value = 100
                    progress_class = "progress-complete"
                else:
                    progress_value = 80
                    progress_class = "progress-incomplete"
                
                # Crear barra de progreso personalizada con HTML puro
                st.markdown(f"""
                <div class="custom-progress-container">
                    <div class="custom-progress-bar {progress_class}" style="width: {progress_value}%"></div>
                </div>
                """, unsafe_allow_html=True)

# Configuración del sidebar
with st.sidebar:
    st.sidebar.title("Opciones de Monitoreo")
    
    # Crear menú desplegable para seleccionar ruta
    ruta_elegida = st.selectbox(
        "Seleccione una ruta del sistema:",
        list(RUTAS_PREDEFINIDAS.keys())
    )
    
    # Obtener la ruta real correspondiente a la etiqueta seleccionada
    directorio_trabajo = RUTAS_PREDEFINIDAS[ruta_elegida]
    
    # Botón para actualizar manualmente
    if st.button("🔄 Actualizar"):
        st.success("Datos actualizados")
    
    # Mostrar información adicional
    st.sidebar.markdown("---")
    st.sidebar.info("""
    **Información:**
    - 🟢 Verde: Archivo con contenido
    - 🟡 Amarillo: Archivo vacío
    """)
    
    # Configurar tiempo de refresco
    refresh_time = st.slider("Tiempo de refresco (segundos)", 5, 300, 60)
    
    # Agregar un refresco automático
    st.markdown(f"""
    <meta http-equiv="refresh" content="{refresh_time}">
    """, unsafe_allow_html=True)

# Verificar si el directorio existe y monitorizar
if not os.path.exists(directorio_trabajo):
    st.error(f"El directorio {directorio_trabajo} no existe.")
else:
    monitorizar_directorio(directorio_trabajo)
