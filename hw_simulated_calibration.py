import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

# 1. PARÁMETROS DE LA SIMULACIÓN
a_real = 0.05
sigma_real = 0.008
r0 = 0.03
years = 7
days_per_year = 252
dt = 1 / days_per_year
n_steps = years * days_per_year
tenors = np.array([1, 2, 3, 4, 5, 7, 10, 15, 20])

# 2. DISCRETIZACIÓN EXACTA DE HULL-WHITE (Short Rate)
# r(t+dt) = r(t)e^{-a dt} + sigma * sqrt((1-e^{-2a dt})/(2a)) * Z
np.random.seed(42)
r = np.zeros(n_steps)
r[0] = r0
vol_adj = np.sqrt(sigma_real**2 / (2 * a_real) * (1 - np.exp(-2 * a_real * dt)))

for t in range(1, n_steps):
    r[t] = r[t-1] * np.exp(-a_real * dt) + vol_adj * np.random.normal()

# 3. CÁLCULO DE YIELDS (TIPO CUPÓN CERO) CONSTANT MATURITY
def get_B(a, tau):
    return (1 - np.exp(-a * tau)) / a

def get_yield_hw(r_t, a, sigma, tau):
    # En HW, el yield R(t, T) es A(t,T) + B(t,T)*r_t, aquí simplificamos 
    # asumiendo curva plana inicial para centrarnos en la volatilidad.
    B = get_B(a, tau)
    # Volatilidad del yield es independiente del nivel r_t si a y sigma son constantes
    # Solo necesitamos la parte estocástica para medir la desviación estándar
    return (B / tau) * r_t

# Generamos series temporales de tipos para cada tenor
yields_dict = {tau: get_yield_hw(r, a_real, sigma_real, tau) for tau in tenors}
df_yields = pd.DataFrame(yields_dict)

# 4. REMUESTREO SEMANAL (Cada 5 días) Y ESTIMACIÓN DE VOLATILIDAD
df_weekly = df_yields.iloc[::5]
# Volatilidad anualizada de los cambios en los tipos (Standard Deviation of Diff)
vols_market = df_weekly.diff().std() * np.sqrt(52) 

# 5. MÉTODO DE LINEALIZACIÓN (OLS - Seed Fit)
# sigma_R approx beta0 + beta1 * T + beta2 * T^2
X = np.column_stack([tenors, tenors**2])
y = vols_market.values
reg = LinearRegression().fit(X, y)

beta0 = reg.intercept_
beta1 = reg.coef_[0]

sigma_seed = beta0
a_seed = -2 * beta1 / beta0

print(f"--- SEMILLA (OLS) ---")
print(f"a_seed: {a_seed:.4f}, sigma_seed: {sigma_seed:.4f}")

# 6. OPTIMIZACIÓN NO LINEAL (NLLS)
def objective(params):
    a, sigma = params
    if a <= 0 or sigma <= 0: return 1e10
    vols_model = sigma * (1 - np.exp(-a * tenors)) / (a * tenors)
    return np.sum((vols_market - vols_model)**2)

res = minimize(objective, x0=[a_seed, sigma_seed], method='L-BFGS-B', bounds=[(1e-5, 1), (1e-5, 0.1)])
a_est, sigma_est = res.x

print(f"\n--- CALIBRACIÓN FINAL (NLLS) ---")
print(f"a_estimado: {a_est:.4f} (Real: {a_real})")
print(f"sigma_estimado: {sigma_est:.4f} (Real: {sigma_real})")

# 7. VISUALIZACIÓN
plt.figure(figsize=(10, 6))
plt.scatter(tenors, vols_market, color='red', label='Volatilidad Simulada (Mercado)')
plt.plot(tenors, sigma_est * (1 - np.exp(-a_est * tenors)) / (a_est * tenors), 
         label=f'Ajuste HW (a={a_est:.3f}, σ={sigma_est:.4f})', linestyle='--')
plt.title('Calibración de Volatilidad Hull-White')
plt.xlabel('Tenor (Años)')
plt.ylabel('Volatilidad del Tipo Cupón Cero')
plt.legend()
plt.grid(True)
plt.show()