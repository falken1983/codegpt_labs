import numpy as np
from scipy.linalg import solve_banded


def valorar_opcion_americana_fdm(S0, K, T, r, sigma, S_max, M, N, option_type="put"):
    """
    Valora una opción americana usando Diferencias Finitas (Esquema Implícito).

    Parámetros:
    S0      : Precio actual del activo
    K       : Precio de ejercicio (Strike)
    T       : Tiempo al vencimiento
    r       : Tasa libre de riesgo
    sigma   : Volatilidad
    S_max   : Valor máximo de la malla (debe ser >> K)
    M       : Número de pasos en el espacio (precios)
    N       : Número de pasos en el tiempo
    option_type: 'put' o 'call'
    """

    # 1. Discretización de la malla
    dt = T / N
    ds = S_max / M
    s_values = np.linspace(0, S_max, M + 1)

    # 2. Inicialización de la opción (Condición terminal: Payoff al vencimiento)
    if option_type == "put":
        V = np.maximum(K - s_values, 0)
    else:
        V = np.maximum(s_values - K, 0)

    # 3. Construcción de la matriz tridiagonal (Esquema Implícito)
    # La ecuación de Black-Scholes discretizada es:
    # a_i * V_{i-1, t} + b_i * V_{i, t} + c_i * V_{i+1, t} = V_{i, t+dt}

    i = np.arange(1, M)  # Índices internos de la malla
    s_i = s_values[1:-1]

    # Coeficientes de la discretización (Diferencias finitas de segundo orden)
    diffusion = dt * 0.5 * sigma**2 * i**2
    drift = dt * 0.5 * r * i

    # Coeficientes para la matriz tridiagonal (A * V_new = V_old)
    A_lower = -(diffusion - drift)
    A_main = 1.0 + 2 * diffusion + r * dt
    A_upper = -(diffusion + drift)

    # 4. Preparación de la matriz para solve_banded (Formato Scipy)
    ab = np.zeros((3, M - 1))
    ab[0, 1:] = A_upper[:-1]  # Diagonal superior en la fila 0
    ab[1, :] = A_main  # Diagonal principal
    ab[2, :-1] = A_lower[1:]  # Diagonal inferior en la fila 2

    # 5. Iteración temporal hacia atrás (Backward in time)
    for n in range(N):
        # 7. Condiciones de frontera (S=0 y S=S_max) evaluadas en t
        t_remaining = (n + 1) * dt
        if option_type == "put":
            V[0] = K
            V[M] = 0
        else:
            V[0] = 0
            V[M] = s_values[M] - K * np.exp(-r * t_remaining)

        b = V[1:-1].copy()

        # Ajuste de los extremos del vector b con las condiciones de frontera actuales
        b[0] -= A_lower[0] * V[0]
        b[-1] -= A_upper[-1] * V[M]

        # Resolución del sistema lineal: A * V_new = b
        V_new_inner = solve_banded((1, 1), ab, b)

        # Actualizamos los valores internos de la malla
        V[1:-1] = V_new_inner

        # 6. CONDICIÓN DE FRONTERA LIBRE (Ejercicio Americano)
        if option_type == "put":
            V = np.maximum(V, K - s_values)
        else:
            V = np.maximum(V, s_values - K)

    return np.interp(S0, s_values, V)


# --- Bloque de Prueba ---
if __name__ == "__main__":
    # Parámetros de la simulación (iguales al script de Monte Carlo)
    S0 = 100.0
    K = 105.0
    T = 1.0
    r = 0.05
    sigma = 0.2

    # Parámetros de la malla FDM
    S_max = 250  # Suficientemente alto para que la frontera no afecte
    M = 200  # Pasos en espacio
    N = 500  # Pasos en tiempo

    print("--- Valoración de Opción Americana (Diferencias Finitas - Implícito) ---")
    try:
        precio_fdm = valorar_opcion_americana_fdm(
            S0, K, T, r, sigma, S_max, M, N, "put"
        )
        print(f"Precio de la Opción Put: {precio_fdm:.4f}")
    except Exception as e:
        print(f"Error en la ejecución: {e}")
