import numpy as np
from scipy.stats import norm

import fdm_american_eqopt as fdm
import montecarlo_american_eqopt as mc


def valorar_black_scholes_analitico(S0, K, T, r, sigma, option_type="call"):
    """

    Implementación analítica de la fórmula de Black-Scholes para opciones Europeas.
    """
    d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        price = S0 * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S0 * norm.cdf(-d1)

    return price


def run_comparison():
    # --- Parámetros de la prueba ---
    # Usaremos una CALL para demostrar que Americana == Europea (sin dividendos)
    S0 = 100.0
    K = 100.0
    T = 1.0
    r = 0.05
    sigma = 0.2
    option_type = "call"

    # Parámetros específicos para métodos numéricos
    N_paths = 20000
    N_steps_mc = 100
    S_max_fdm = 300.0
    M_fdm = 200
    N_fdm = 500

    print(f"=== Comparación de Métodos de Valoración ({option_type.upper()}) ===")
    print(f"Parámetros: S0={S0}, K={K}, T={T}, r={r}, sigma={sigma}")
    print("-" * 60)

    # 1. Método Analítico (Black-Scholes)
    try:
        p_bs = valorar_black_scholes_analitico(S0, K, T, r, sigma, option_type)
        print(f"[1] Black-Scholes (Analítico):  {p_bs:.6f}")
    except Exception as e:
        print(f"[1] Black-Scholes Error: {e}")

    # 2. Método Monte Carlo (Longstaff-Schwartz)
    try:
        # Nota: El script original de MC tiene hardcoded 'payoffs' como Call.
        # Para ser fiel al script proporcionado, asumimos que mide Call.
        p_mc = mc.valorar_opcion_americana_mc(S0, K, T, r, sigma, N_steps_mc, N_paths)
        print(f"[2] Monte Carlo (LSMC):       {p_mc:.6f}")
    except Exception as e:
        print(f"[2] Monte Carlo Error: {e}")

    # 3. Método Diferencias Finitas (FDM)
    try:
        p_fdm = fdm.valorar_opcion_americana_fdm(
            S0, K, T, r, sigma, S_max_fdm, M_fdm, N_fdm, option_type
        )
        print(f"[3] Diferencias Finitas (FDM): {p_fdm:.6f}")
    except Exception as e:
        print(f"[3] FDM Error: {e}")

    # --- Cálculo de Errores Relativos respecto al Analítico ---
    print("-" * 60)
    if "p_bs" in locals():
        err_mc = abs(p_mc - p_bs) / p_bs if "p_mc" in locals() else None
        err_fdm = abs(p_fdm - p_bs) / p_bs if "p_fdm" in locals() else None

        if err_mc:
            print(f"Error Relativo MC: {err_mc:.4%}")
        if err_fdm:
            print(f"Error Relativo FDM: {err_fdm:.4%}")


if __name__ == "__main__":
    run_comparison()
