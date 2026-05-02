import os
import xml.dom.minidom
import xml.etree.ElementTree as ET


class SimulationBuilder:
    """
    Clase encargada de construir los archivos XML `simulation.xml` que
    definen los modelos de pricing, las dependencias cruzadas (CrossAsset)
    y los parámetros de calibración de inflación para ORE.
    """

    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.inflation_indices = {"EUR": "EUHICPXT", "GBP": "UKRPI", "USD": "USCPI"}

    def _prettify_xml(self, elem):
        """Devuelve un string XML con formato indentado (pretty print)."""
        rough_string = ET.tostring(elem, "utf-8")
        reparsed = xml.dom.minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def _add_jarrow_yildirim_model(self, parent_node, ccy, index, calib_reversion):
        """Añade la especificación del modelo JY para una divisa dada."""
        jy_node = ET.SubElement(parent_node, "JarrowYildirim")
        jy_node.set("index", index)

        ET.SubElement(jy_node, "Currency").text = ccy
        ET.SubElement(jy_node, "CalibrationType").text = "BestFit"

        # Baskets de Calibración
        baskets = ET.SubElement(jy_node, "CalibrationBaskets")

        # Basket para Índice (CpiCapFloors)
        idx_basket = ET.SubElement(baskets, "CalibrationBasket")
        idx_basket.set("parameter", "Index")
        for tenor in ["2Y", "5Y", "7Y", "10Y", "20Y"]:
            cpf = ET.SubElement(idx_basket, "CpiCapFloor")
            ET.SubElement(cpf, "Type").text = "Floor"
            ET.SubElement(cpf, "Maturity").text = tenor
            ET.SubElement(cpf, "Strike").text = "0.0"

        # Basket para Tasa Real (YoYSwaps - Usado como proxy estándar en ORE para calibrar real rate)
        rr_basket = ET.SubElement(baskets, "CalibrationBasket")
        rr_basket.set("parameter", "RealRate")
        for tenor in ["2Y", "5Y", "7Y", "10Y", "20Y"]:
            swap = ET.SubElement(rr_basket, "YoYSwap")
            ET.SubElement(swap, "Tenor").text = tenor

        # Tasa Real: Volatilidad y Reversión
        real_rate = ET.SubElement(jy_node, "RealRate")

        rr_vol = ET.SubElement(real_rate, "Volatility")
        ET.SubElement(rr_vol, "VolatilityType").text = "Hagan"
        ET.SubElement(rr_vol, "Calibrate").text = "Y"
        ET.SubElement(rr_vol, "ParamType").text = "Piecewise"
        ET.SubElement(rr_vol, "TimeGrid")
        ET.SubElement(rr_vol, "InitialValue").text = "0.01"

        rr_rev = ET.SubElement(real_rate, "Reversion")
        ET.SubElement(rr_rev, "ReversionType").text = "HullWhite"
        ET.SubElement(rr_rev, "Calibrate").text = "Y" if calib_reversion else "N"
        ET.SubElement(rr_rev, "ParamType").text = "Constant"
        ET.SubElement(rr_rev, "TimeGrid")
        ET.SubElement(rr_rev, "InitialValue").text = "0.5"

        rr_pt = ET.SubElement(real_rate, "ParameterTransformation")
        ET.SubElement(rr_pt, "ShiftHorizon").text = "0.0"
        ET.SubElement(rr_pt, "Scaling").text = "1.0"

        # Índice: Volatilidad
        idx_node = ET.SubElement(jy_node, "Index")
        idx_vol = ET.SubElement(idx_node, "Volatility")
        ET.SubElement(idx_vol, "Calibrate").text = "Y"
        ET.SubElement(idx_vol, "ParamType").text = "Piecewise"
        ET.SubElement(idx_vol, "TimeGrid")
        ET.SubElement(idx_vol, "InitialValue").text = "0.01"

        # Configuración de Algoritmo de Calibración
        calib_config = ET.SubElement(jy_node, "CalibrationConfiguration")
        ET.SubElement(calib_config, "RmseTolerance").text = "0.00000001"
        ET.SubElement(calib_config, "MaxIterations").text = "50"

    def _add_dk_model(self, parent_node, ccy, index, calib_reversion):
        """Añade la especificación del modelo DK (LGM de Inflación) para una divisa dada."""
        lgm_node = ET.SubElement(parent_node, "LGM")
        lgm_node.set("index", index)

        ET.SubElement(lgm_node, "Currency").text = ccy
        ET.SubElement(lgm_node, "CalibrationType").text = "BestFit"

        # Volatilidad
        vol = ET.SubElement(lgm_node, "Volatility")
        ET.SubElement(vol, "Calibrate").text = "Y"
        ET.SubElement(vol, "VolatilityType").text = "Hagan"
        ET.SubElement(vol, "ParamType").text = "Piecewise"
        ET.SubElement(vol, "TimeGrid").text = "2.0, 5.0, 7.0, 10.0, 20.0"
        ET.SubElement(vol, "InitialValue").text = "0.01, 0.01, 0.01, 0.01, 0.01, 0.01"

        # Reversión
        rev = ET.SubElement(lgm_node, "Reversion")
        ET.SubElement(rev, "Calibrate").text = "Y" if calib_reversion else "N"
        ET.SubElement(rev, "ReversionType").text = "Hagan"
        ET.SubElement(rev, "ParamType").text = "Piecewise"
        ET.SubElement(rev, "TimeGrid").text = "2.0, 5.0, 7.0, 10.0, 20.0"
        ET.SubElement(rev, "InitialValue").text = "0.5, 0.5, 0.5, 0.5, 0.5, 0.5"

        # Instrumentos de calibración (Caps/Floors)
        caps = ET.SubElement(lgm_node, "CalibrationCapFloors")
        ET.SubElement(caps, "CapFloor").text = "Floor"
        ET.SubElement(caps, "Expiries").text = "2Y, 5Y, 7Y, 10Y, 20Y"
        ET.SubElement(caps, "Strikes").text = "0.0, 0.0, 0.0, 0.0, 0.0"

        pt = ET.SubElement(lgm_node, "ParameterTransformation")
        ET.SubElement(pt, "ShiftHorizon").text = "0.0"
        ET.SubElement(pt, "Scaling").text = "1.0"

    def build_simulation_xml(self, model_type, free_reversion=True):
        """
        Construye el archivo simulation.xml requerido para la calibración
        de CrossAssetModels.

        :param model_type: 'jy' para Jarrow-Yildirim, 'dk' para Dodgson-Kainth.
        :param free_reversion: Boolean. True si la reversión es un parámetro libre, False si es fija.
        """
        root = ET.Element("Simulation")

        # Parámetros Globales
        params = ET.SubElement(root, "Parameters")
        ET.SubElement(params, "Discretization").text = "Exact"
        ET.SubElement(params, "Grid").text = "81,3M"
        ET.SubElement(params, "Calendar").text = "EUR,GBP,USD"
        ET.SubElement(params, "Sequence").text = "SobolBrownianBridge"
        ET.SubElement(params, "Scenario").text = "Simple"
        ET.SubElement(params, "Seed").text = "42"
        ET.SubElement(params, "Samples").text = "1000"

        # Modelo Cross Asset
        cam = ET.SubElement(root, "CrossAssetModel")
        ET.SubElement(cam, "DomesticCcy").text = "EUR"

        ccys_node = ET.SubElement(cam, "Currencies")
        for ccy in self.inflation_indices.keys():
            ET.SubElement(ccys_node, "Currency").text = ccy

        idx_node = ET.SubElement(cam, "InflationIndices")
        for idx in self.inflation_indices.values():
            ET.SubElement(idx_node, "InflationIndex").text = idx

        ET.SubElement(cam, "BootstrapTolerance").text = "0.0001"

        # En una calibración de inflación pura, normalmente los modelos IR y FX
        # se asumen pre-calibrados o se proveen mínimos fijos para satisfacer dependencias.
        # Por simplicidad en la interfaz, omitimos IR/FX Models complejos asumiendo
        # que nos centramos en los bloques de Inflación.

        # Modelos de Inflación
        inf_models = ET.SubElement(cam, "InflationIndexModels")

        for ccy, index in self.inflation_indices.items():
            if model_type.lower() == "jy":
                self._add_jarrow_yildirim_model(inf_models, ccy, index, free_reversion)
            elif model_type.lower() == "dk":
                self._add_dk_model(inf_models, ccy, index, free_reversion)
            else:
                raise ValueError(f"Tipo de modelo no soportado: {model_type}")

        # Correlaciones instantáneas (Vacías/Cero para simplificar calibración marginal)
        ET.SubElement(cam, "InstantaneousCorrelations")
        # Se añadirían las correlaciones si fueran parte del requerimiento,
        # pero la calibración estándar se suele hacer sobre las volatilidades
        # asumiendo parámetros marginales primero.

        # Mercado de Simulación (Requerido por ORE aunque se calibre)
        market = ET.SubElement(root, "Market")
        ET.SubElement(market, "BaseCurrency").text = "EUR"

        ccys_mkt = ET.SubElement(market, "Currencies")
        for ccy in self.inflation_indices.keys():
            ET.SubElement(ccys_mkt, "Currency").text = ccy

        cpi_mkt = ET.SubElement(market, "CpiIndices")
        for idx in self.inflation_indices.values():
            ET.SubElement(cpi_mkt, "Index").text = idx

        zc_mkt = ET.SubElement(market, "ZeroInflationIndexCurves")
        names_zc = ET.SubElement(zc_mkt, "Names")
        for idx in self.inflation_indices.values():
            ET.SubElement(names_zc, "Name").text = idx
        ET.SubElement(zc_mkt, "Tenors").text = "1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y"

        xml_str = self._prettify_xml(root)

        mode_str = "free" if free_reversion else "fixed"
        filename = f"simulation_{model_type}_{mode_str}.xml"
        out_path = os.path.join(self.output_dir, filename)

        with open(out_path, "w") as f:
            f.write(xml_str)

        return out_path
