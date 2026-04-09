import numpy as np
import QuantLib as ql


def valorar_opcion_americana_mc(
    spot, strike, maturity, risk_free_rate, volatility, steps, paths, option_type="call"
):
    """
    Valora una opción de estilo americano usando la simulación de Monte Carlo
    con el método de Longstaff-Schwartz.
    """

    # 1. Configuración de fechas
    today = ql.Date().todaysDate()
    ql.Settings.instance().evaluationDate = today

    # Definir el vencimiento
    maturity_date = today + ql.Period(int(maturity), ql.Years)

    # 2. Configuración del proceso estocástico (Black-Scholes)
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
    risk_free_rate_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(today, risk_free_rate, ql.Actual365Fixed())
    )
    volatility_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(today, ql.NullCalendar(), volatility, ql.Actual365Fixed())
    )

    bsm_process = ql.BlackScholesProcess(
        spot_handle, risk_free_rate_handle, volatility_handle
    )

    # 3. Generación de trayectorias de Monte Carlo
    # Nota: QuantLib tiene implementaciones de LSMC, pero aquí simularemos la lógica
    # para que veas el proceso matemático subyacente.

    dt = maturity / steps
    discount_factor = np.exp(-risk_free_rate * dt)

    # Matriz de trayectorias (paths x steps + 1)
    trajectories = np.zeros((paths, steps + 1))
    trajectories[:, 0] = spot

    for i in range(1, steps + 1):
        # Generamos retornos normales estandarizados
        z = np.random.standard_normal(paths)
        # Fórmula de Euler-Maruyama para GBM
        trajectories[:, i] = trajectories[:, i - 1] * np.exp(
            (risk_free_rate - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * z
        )

    # 4. Algoritmo de Longstaff-Schwartz (Regresión para ejercicio temprano)
    if option_type == "put":
        payoffs = np.maximum(strike - trajectories[:, -1], 0)
    else:
        payoffs = np.maximum(trajectories[:, -1] - strike, 0)

    # Trabajamos hacia atrás desde el vencimiento
    cash_flows = payoffs

    for t in range(steps, 0, -1):
        # Valores intrínsecos (Payoff si se ejerce ahora)
        if option_type == "put":
            exercise_now = np.maximum(strike - trajectories[:, t], 0)
        else:
            exercise_now = np.maximum(trajectories[:, t] - strike, 0)

        # Solo consideramos trayectorias "In-the-money" para la regresión
        itm_indices = np.where(exercise_now > 0)[0]

        if len(itm_indices) > 0:
            # Variables predictoras (X): precio de la acción actual
            X = trajectories[itm_indices, t]
            # Variable objetivo (Y): valor de los flujos futuros traídos al tiempo 't'
            # Nota: cash_flows ya contiene el valor de los flujos de t+1
            Y = cash_flows[itm_indices]

            # Fit de polinomio (grado 2) para estimar el valor de continuación
            # Usamos un polinomio simple: 1, x, x^2
            X_poly = np.column_stack([np.ones_like(X), X, X**2])
            weights = np.linalg.lstsq(X_poly, Y, rcond=None)[0]

            continuation_value = np.dot(X_poly, weights)

            # Decisión: ¿Es el ejercicio inmediato mayor que el valor de continuación?
            exercise_decision = exercise_now[itm_indices] > continuation_value

            # Actualizamos los cash flows:
            # Si decidimos ejercer, el nuevo cash flow es el payoff actual.
            # Si NO decidimos ejercer, el cash flow se mantiene (el valor descontado que ya teníamos).
            actual_indices_in_itm = itm_indices[exercise_decision]
            cash_flows[actual_indices_in_itm] = exercise_now[
                itm_indices[exercise_decision]
            ]

        # Descontar todos los cash flows un paso más hacia atrás para la siguiente iteración
        cash_flows *= discount_factor

    # 5. Resultado final
    option_price = np.mean(cash_flows)
    return option_price


# --- Parámetros de Simulación ---
S0 = 100.0  # Precio actual de la acción
K = 105.0  # Precio de ejercicio (Strike)
T = 1.0  # Tiempo al vencimiento (1 año)
r = 0.05  # Tasa libre de riesgo (5%)
sigma = 0.2  # Volatilidad (25%)
N_steps = 500  # Pasos de tiempo en la simulación
N_paths = 100000  # Número de trayectorías de Monte Carlo
option_type = "put"  # 'put' o 'call'

precio_estimado = valorar_opcion_americana_mc(
    S0, K, T, r, sigma, N_steps, N_paths, option_type
)

print("--- Simulación Monte Carlo (Longstaff-Schwartz) ---")
print(f"Precio de la Opción Americana ({option_type.upper()}): {precio_estimado:.4f}")
