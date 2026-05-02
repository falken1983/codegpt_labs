import os

from .market_data_converter import MarketDataConverter
from .simulation_builder import SimulationBuilder


class MainController:
    """
    Controlador principal que orquesta la creación de todos los ficheros
    requeridos para calibrar modelos de inflación en ORE-Python, tomando
    como fuente datos de mercado CSV genéricos.
    """

    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.converter = MarketDataConverter(output_dir=self.output_dir)
        self.builder = SimulationBuilder(output_dir=self.output_dir)

    def prepare_market_data(
        self, yield_csv=None, inf_swaps_csv=None, caps_csv=None, fixings_csv=None
    ):
        """
        Paso 1: Genera los archivos estáticos de configuración de mercado
        (curveconfig, todaysmarket) y convierte los CSV de mercado al
        formato nativo de ORE.
        """
        print("1. Preparando entorno y traduciendo datos de mercado externos...")
        paths = self.converter.convert_all(
            yield_csv, inf_swaps_csv, caps_csv, fixings_csv
        )
        for key, path in paths.items():
            print(f"   - {key}: {path}")
        return paths

    def generate_simulation_configs(self):
        """
        Paso 2: Construye las especificaciones de simulación para los
        modelos Jarrow-Yildirim (JY) y Dodgson-Kainth (DK),
        con parámetros de reversión libres y fijos.
        """
        print("\n2. Construyendo configuraciones de simulación (XML)...")
        sim_files = {}

        # 2. Modelo Jarrow-Yildirim (JY)
        sim_files["jy_free"] = self.builder.build_simulation_xml(
            model_type="jy", free_reversion=True
        )
        sim_files["jy_fixed"] = self.builder.build_simulation_xml(
            model_type="jy", free_reversion=False
        )

        # 4. Modelo Dodgson-Kainth (DK)
        sim_files["dk_free"] = self.builder.build_simulation_xml(
            model_type="dk", free_reversion=True
        )
        sim_files["dk_fixed"] = self.builder.build_simulation_xml(
            model_type="dk", free_reversion=False
        )

        for name, path in sim_files.items():
            print(f"   - {name}: {path}")

        return sim_files

    def generate_ore_master_configs(self, sim_files):
        """
        Paso 3: Genera los archivos maestros (ore.xml) para cada caso
        de calibración.
        """
        print("\n3. Generando archivos maestros de ORE (ore_*.xml)...")
        ore_configs = {}

        for model_id, sim_file_path in sim_files.items():
            sim_filename = os.path.basename(sim_file_path)

            # Nota: portfolio_{model_id[:2]}.xml es un placeholder para carteras
            # dummy de calibración si el motor de ORE lo requiere estructuralmente.
            xml_content = f"""<ORE>
  <Setup>
    <Parameter name="asofDate">2020-11-02</Parameter>
    <Parameter name="inputPath">{self.output_dir}</Parameter>
    <Parameter name="outputPath">Output/{model_id}</Parameter>
    <Parameter name="logFile">log_{model_id}.txt</Parameter>
    <Parameter name="logMask">31</Parameter>
    <Parameter name="marketDataFile">market.txt</Parameter>
    <Parameter name="fixingDataFile">fixings.txt</Parameter>
    <Parameter name="implyTodaysFixings">Y</Parameter>
    <Parameter name="curveConfigFile">curveconfig.xml</Parameter>
    <Parameter name="conventionsFile">conventions.xml</Parameter>
    <Parameter name="marketConfigFile">todaysmarket.xml</Parameter>
    <Parameter name="pricingEnginesFile">pricingengine.xml</Parameter>
    <Parameter name="portfolioFile">portfolio_{model_id[:2]}.xml</Parameter>
    <Parameter name="observationModel">None</Parameter>
  </Setup>
  <Markets>
    <Parameter name="lgmcalibration">default</Parameter>
    <Parameter name="fxcalibration">default</Parameter>
    <Parameter name="infcalibration">default</Parameter>
    <Parameter name="pricing">default</Parameter>
    <Parameter name="simulation">default</Parameter>
  </Markets>
  <Analytics>
    <Analytic type="calibration">
      <Parameter name="active">Y</Parameter>
      <Parameter name="configFile">{sim_filename}</Parameter>
      <Parameter name="outputFile">calibration.csv</Parameter>
    </Analytic>
  </Analytics>
</ORE>
"""
            ore_file = os.path.join(self.output_dir, f"ore_{model_id}.xml")
            with open(ore_file, "w") as f:
                f.write(xml_content)

            ore_configs[model_id] = ore_file
            print(f"   - {model_id}: {ore_file}")

        return ore_configs

    def run_pipeline(
        self, yield_csv=None, inf_swaps_csv=None, caps_csv=None, fixings_csv=None
    ):
        """
        Ejecuta el pipeline completo de preparación.
        """
        print("=== Iniciando Pipeline de Configuración para ORE ===")
        self.prepare_market_data(yield_csv, inf_swaps_csv, caps_csv, fixings_csv)
        sim_files = self.generate_simulation_configs()
        ore_configs = self.generate_ore_master_configs(sim_files)

        print("\n=== Pipeline completado ===")
        print("Los archivos están listos para ser consumidos por OREApp.")
        return ore_configs


if __name__ == "__main__":
    # Test local run
    controller = MainController()
    controller.run_pipeline()
