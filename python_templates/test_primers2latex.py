def es_primo(num):
    if num <= 1:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True

def primeros_100_numeros_primos():
    primos = []
    numero = 2
    while len(primos) < 100:
        if es_primo(numero):
            primos.append(numero)
        numero += 1
    return primos

def generar_tabla_latex(primos):
    contenido = "\\documentclass{article}\n\\usepackage{array}\n\n\\begin{document}\n\n"
    contenido += "\\begin{table}[h]\n    \\centering\n    \\caption{Primeros 100 Números Primos}\n    \\label{tab:primos}\n    \\begin{tabular}{*{10}{c}}\n        \\hline\n        \\textbf{Número} & \\textbf{Número} & \\textbf{Número} & \\textbf{Número} & \\textbf{Número} \\\\\n        \\hline\n"
    
    for i in range(0, len(primos), 5):
        fila = "        "
        for j in range(i, min(i + 5, len(primos))):
            fila += f"{primos[j]} & "
        contenido += fila.strip()[:-1] + "\\\\\n"
    
    contenido += "\\end{tabular}\n\\end{table}\n\n\\end{document}"
    return contenido

primos = primeros_100_numeros_primos()
latex_code = generar_tabla_latex(primos)

with open("primos.tex", "w") as file:
    file.write(latex_code)
