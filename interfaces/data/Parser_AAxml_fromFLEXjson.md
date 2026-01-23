Considera la representación en json de un trade Acumulador Europeo: fichero `trade*json`
Considera la representacion en XML de FIS Adaptiv Analytics (AA) del mismo trade: fichero sin Portfolio `*xml`
Construye un parser en Python que:

1. Traduzca el trade de la representación JSON al XML compliant con FIS AA
2. Dado un folder con trades en formato JSON, recorra json a json y si es un trade (clave "__type__" = "Trade", lo traslade a la representación AA XML y finalmente genere un Portfolio completo con todos los trades traducidos (fíjate en la estructura completa del AA XML `Portfolio*`.
3. Debes implementar un logging que recoja cualquier tipo de error trade a trade
4. Fíjate en los formatos de fecha. En JSON se utiliza formato Excel (OLE) en AA se utiliza String tipo ddMMMyyyy
5. Debes utilizar la última y la primera fecha de FDATE en JSON para informar First y Last_Observation_Date. Deduce la Observation_Frequency=num + "W" (W de week) a partir de las FDATE en JSON (por defecto, utiliza siempre 1W)