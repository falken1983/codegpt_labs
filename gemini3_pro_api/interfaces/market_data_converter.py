import csv
import os
import xml.dom.minidom
import xml.etree.ElementTree as ET


class MarketDataConverter:
    """
    Interface para convertir datos de mercado externos (CSV) a la
    especificación necesaria (XML, TXT) para ORE-Python.
    Soporta configuraciones para GBP, USD y EUR.
    """

    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.supported_ccys = ["EUR", "GBP", "USD"]
        self.inflation_indices = {"EUR": "EUHICPXT", "GBP": "UKRPI", "USD": "USCPI"}

    def _prettify_xml(self, elem):
        """Devuelve un string XML con formato indentado (pretty print)."""
        rough_string = ET.tostring(elem, "utf-8")
        reparsed = xml.dom.minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def generate_market_txt(self, yield_curves_csv, inflation_swaps_csv, cpi_caps_csv):
        """
        Genera el archivo market.txt requerido por ORE a partir de CSVs.

        Formatos esperados de CSV (sin cabecera o ignorada si empieza por #):
        - yield_curves_csv: Fecha, ID_Curva, Tenor, Tasa
        - inflation_swaps_csv: Fecha, ID_Indice, Tenor, Tasa
        - cpi_caps_csv: Fecha, ID_Indice, Tenor, Strike, Volatilidad
        """
        out_path = os.path.join(self.output_dir, "market.txt")

        with open(out_path, "w") as f_out:
            f_out.write("# Fecha Ticker Valor\n")

            if yield_curves_csv and os.path.exists(yield_curves_csv):
                with open(yield_curves_csv, "r") as f_in:
                    for row in csv.reader(f_in):
                        if (
                            not row
                            or row[0].startswith("#")
                            or row[0].lower() == "fecha"
                        ):
                            continue
                        date, ccy, tenor, rate = row[:4]
                        ticker = f"ZERO/YIELD/{ccy.strip()}/OIS/{tenor.strip()}"
                        f_out.write(f"{date.strip()} {ticker} {rate.strip()}\n")

            if inflation_swaps_csv and os.path.exists(inflation_swaps_csv):
                with open(inflation_swaps_csv, "r") as f_in:
                    for row in csv.reader(f_in):
                        if (
                            not row
                            or row[0].startswith("#")
                            or row[0].lower() == "fecha"
                        ):
                            continue
                        date, index, tenor, rate = row[:4]
                        ticker = f"ZERO/INFLATION/{index.strip()}/{tenor.strip()}"
                        f_out.write(f"{date.strip()} {ticker} {rate.strip()}\n")

            if cpi_caps_csv and os.path.exists(cpi_caps_csv):
                with open(cpi_caps_csv, "r") as f_in:
                    for row in csv.reader(f_in):
                        if (
                            not row
                            or row[0].startswith("#")
                            or row[0].lower() == "fecha"
                        ):
                            continue
                        date, index, tenor, strike, vol = row[:5]
                        ticker = f"INF_CAPFLOOR/VOL/{index.strip()}/{tenor.strip()}/{strike.strip()}"
                        f_out.write(f"{date.strip()} {ticker} {vol.strip()}\n")

        return out_path

    def generate_fixings_txt(self, fixings_csv):
        """
        Genera el archivo fixings.txt requerido por ORE a partir de un CSV.

        Formato esperado de CSV:
        - fixings_csv: Fecha, ID_Indice, Valor
        """
        out_path = os.path.join(self.output_dir, "fixings.txt")
        with open(out_path, "w") as f_out:
            f_out.write("# Fecha Ticker Valor\n")

            if fixings_csv and os.path.exists(fixings_csv):
                with open(fixings_csv, "r") as f_in:
                    for row in csv.reader(f_in):
                        if (
                            not row
                            or row[0].startswith("#")
                            or row[0].lower() == "fecha"
                        ):
                            continue
                        date, index, value = row[:3]
                        f_out.write(f"{date.strip()} {index.strip()} {value.strip()}\n")

        return out_path

    def generate_curve_config(self):
        """
        Genera curveconfig.xml dinámicamente configurado para EUR, USD, GBP.
        """
        root = ET.Element("CurveConfiguration")

        # --- Yield Curves ---
        yield_curves = ET.SubElement(root, "YieldCurves")
        for ccy in self.supported_ccys:
            yc = ET.SubElement(yield_curves, "YieldCurve")
            ET.SubElement(yc, "CurveId").text = f"Discount_{ccy}"
            ET.SubElement(yc, "CurveDescription").text = f"{ccy} Discount Curve"
            ET.SubElement(yc, "Currency").text = ccy
            ET.SubElement(yc, "DiscountCurve").text = f"Discount_{ccy}"
            # Se asume una estructura tipo OIS para descuento
            segments = ET.SubElement(yc, "Segments")
            seg = ET.SubElement(segments, "Direct")
            ET.SubElement(seg, "Type").text = "Discount"
            ET.SubElement(seg, "Quotes").text = f"ZERO/YIELD/{ccy}/OIS/*"
            ET.SubElement(seg, "Conventions").text = f"{ccy}-OIS"

        # --- Inflation Curves ---
        inflation_curves = ET.SubElement(root, "InflationCurves")
        for ccy, index in self.inflation_indices.items():
            ic = ET.SubElement(inflation_curves, "InflationCurve")
            ET.SubElement(ic, "CurveId").text = index
            ET.SubElement(ic, "CurveDescription").text = f"{ccy} Zero Inflation Curve"
            ET.SubElement(ic, "Currency").text = ccy
            ET.SubElement(ic, "NominalTermStructure").text = f"Discount_{ccy}"
            ET.SubElement(ic, "Type").text = "ZC"
            ET.SubElement(ic, "Quotes").text = f"ZERO/INFLATION/{index}/*"
            ET.SubElement(ic, "Conventions").text = f"{index}-ZC"

        # --- Inflation Cap/Floor Volatility Surfaces ---
        inf_vols = ET.SubElement(root, "InflationCapFloorVolatilities")
        for ccy, index in self.inflation_indices.items():
            iv = ET.SubElement(inf_vols, "InflationCapFloorVolatility")
            ET.SubElement(iv, "CurveId").text = index
            ET.SubElement(iv, "CurveDescription").text = f"{ccy} Inflation Volatility"
            ET.SubElement(iv, "Type").text = "ZC"
            ET.SubElement(iv, "Index").text = index
            ET.SubElement(iv, "YieldCurve").text = f"Discount_{ccy}"
            ET.SubElement(iv, "VolatilityType").text = "Lognormal"

        xml_str = self._prettify_xml(root)
        out_path = os.path.join(self.output_dir, "curveconfig.xml")
        with open(out_path, "w") as f:
            f.write(xml_str)

        return out_path

    def generate_todays_market(self):
        """
        Genera todaysmarket.xml especificando qué curvas de curveconfig usar.
        """
        root = ET.Element("TodaysMarket")

        config = ET.SubElement(root, "Configuration")
        config.set("id", "default")

        discounting = ET.SubElement(config, "DiscountingCurves")
        for ccy in self.supported_ccys:
            ET.SubElement(
                discounting, "DiscountingCurve", currency=ccy
            ).text = f"Discount_{ccy}"

        index_forwarding = ET.SubElement(config, "IndexForwardingCurves")
        for ccy in self.supported_ccys:
            ET.SubElement(
                index_forwarding, "Index", name=f"{ccy}-OIS"
            ).text = f"Discount_{ccy}"

        zero_inflation = ET.SubElement(config, "ZeroInflationIndexCurves")
        for ccy, index in self.inflation_indices.items():
            ET.SubElement(
                zero_inflation, "ZeroInflationIndexCurve", name=index
            ).text = index

        # Mapeos de volatilidad para calibración
        inf_vols = ET.SubElement(config, "ZeroInflationCapFloorVolatilities")
        for ccy, index in self.inflation_indices.items():
            ET.SubElement(
                inf_vols, "ZeroInflationCapFloorVolatility", name=index
            ).text = index

        xml_str = self._prettify_xml(root)
        out_path = os.path.join(self.output_dir, "todaysmarket.xml")
        with open(out_path, "w") as f:
            f.write(xml_str)

        return out_path

    def convert_all(
        self, yield_csv=None, inf_swaps_csv=None, caps_csv=None, fixings_csv=None
    ):
        """
        Ejecuta todo el pipeline de conversión de datos.
        """
        paths = {}
        paths["curveconfig"] = self.generate_curve_config()
        paths["todaysmarket"] = self.generate_todays_market()
        paths["market_txt"] = self.generate_market_txt(
            yield_csv, inf_swaps_csv, caps_csv
        )
        paths["fixings_txt"] = self.generate_fixings_txt(fixings_csv)

        return paths
