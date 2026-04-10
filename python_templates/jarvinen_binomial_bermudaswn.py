import numpy as np
from scipy import stats

class BinomialInterestRateTree:
    def __init__(self, zero_rates, volatility, time_steps):
        """
        Inicializa el árbol binomial para tipos de interés
        
        Parámetros:
        zero_rates -- diccionario con vencimientos (en años) como claves y tasas cero-cupón como valores
        volatility -- volatilidad anualizada de los tipos de interés
        time_steps -- número de pasos temporales en el árbol
        """
        self.zero_rates = zero_rates
        self.volatility = volatility
        self.time_steps = time_steps
        self.dt = max(zero_rates.keys()) / time_steps
        
        # Construir el árbol
        self.build_tree()
        
    def build_tree(self):
        """
        Construye el árbol binomial para los tipos de interés
        utilizando la calibración de Jarvinen para ajustarse a la curva de tipos inicial
        """
        # Inicializar arrays para almacenar tasas y factores de descuento
        self.rates = np.zeros((self.time_steps + 1, self.time_steps + 1))
        self.discount_factors = np.zeros((self.time_steps + 1, self.time_steps + 1))
        
        # Establecer la tasa inicial (raíz del árbol)
        maturities = sorted(self.zero_rates.keys())
        initial_rate = self.zero_rates[maturities[0]]
        self.rates[0, 0] = initial_rate
        
        # Factores de crecimiento hacia arriba y hacia abajo
        u = np.exp(self.volatility * np.sqrt(self.dt))
        d = 1/u
        
        # Probabilidad de movimiento hacia arriba (modelo de Hull-White)
        self.p = 0.5
        
        # Construir el árbol forward
        for i in range(1, self.time_steps + 1):
            # Calcular tasas para cada nodo en el tiempo i
            for j in range(i + 1):
                up_moves = j
                down_moves = i - j
                self.rates[i, j] = initial_rate * (u ** up_moves) * (d ** down_moves)
            
            # Calcular el ajuste para calibrar el árbol a la curva de tipos zero
            closest_maturity = min(maturities, key=lambda x: abs(x - i*self.dt))
            market_zero_rate = self.zero_rates[closest_maturity]
            
            # Ajustar las tasas para que coincidan con la curva de mercado
            adjustment = market_zero_rate / np.sum([self.rates[i, j] * self.binomial_probability(i, j, self.p) for j in range(i + 1)])
            for j in range(i + 1):
                self.rates[i, j] *= adjustment
        
        # Calcular factores de descuento para cada nodo
        for i in range(self.time_steps + 1):
            for j in range(i + 1):
                self.discount_factors[i, j] = np.exp(-self.rates[i, j] * self.dt)
    
    def binomial_probability(self, n, k, p):
        """
        Calcula la probabilidad binomial de obtener k éxitos en n pruebas
        con una probabilidad de éxito p por prueba
        """
        return stats.binom.pmf(k, n, p)
    
    def value_swaption_bermuda(self, strike, swap_tenor, exercise_dates, notional=1.0):
        """
        Valora un swaption bermuda
        
        Parámetros:
        strike -- tipo fijo del swap subyacente
        swap_tenor -- duración del swap subyacente en años
        exercise_dates -- lista de fechas de ejercicio potenciales (en años)
        notional -- importe nominal del swap
        
        Retorna:
        Valor del swaption bermuda
        """
        # Convertir fechas de ejercicio a índices en el árbol
        exercise_indices = [int(date / self.dt) for date in exercise_dates]
        
        # Número de períodos de pago por año (asumimos pagos anuales)
        payment_frequency = 1
        
        # Inicializar la matriz de valores de la opción
        option_values = np.zeros((self.time_steps + 1, self.time_steps + 1))
        
        # Calcular los valores en los nodos terminales
        for j in range(self.time_steps + 1):
            # Valor del swap en el vencimiento
            swap_value = self._value_swap(self.time_steps, j, strike, swap_tenor, payment_frequency, notional)
            option_values[self.time_steps, j] = max(0, swap_value)
        
        # Retropropagación y aplicación de la lógica de ejercicio óptimo
        for i in range(self.time_steps - 1, -1, -1):
            for j in range(i + 1):
                # Calcular el valor de continuación
                continuation_value = (self.p * option_values[i+1, j+1] + (1-self.p) * option_values[i+1, j]) * self.discount_factors[i, j]
                
                # Si estamos en una fecha de ejercicio, comparar con el valor de ejercicio inmediato
                if i in exercise_indices:
                    swap_value = self._value_swap(i, j, strike, swap_tenor, payment_frequency, notional)
                    option_values[i, j] = max(swap_value, continuation_value)
                else:
                    option_values[i, j] = continuation_value
        
        return option_values[0, 0]
    
    def _value_swap(self, time_index, state_index, strike, swap_tenor, payment_frequency, notional):
        """
        Calcula el valor de un swap de tipos de interés en un nodo específico del árbol
        """
        # Número de pagos restantes
        remaining_payments = int(swap_tenor * payment_frequency)
        
        if remaining_payments == 0:
            return 0
        
        # Valor presente de la pata fija
        fixed_leg = 0
        for k in range(1, remaining_payments + 1):
            payment_time = time_index + k / payment_frequency
            payment_time_index = min(int(payment_time / self.dt), self.time_steps)
            
            # Valor esperado del factor de descuento para el tiempo de pago
            expected_df = 0
            for m in range(payment_time_index + 1):
                prob = self.binomial_probability(payment_time_index - time_index, m - state_index, self.p)
                if 0 <= m <= payment_time_index:
                    expected_df += prob * np.exp(-self.rates[payment_time_index, m] * (payment_time_index - time_index) * self.dt)
            
            fixed_leg += strike * notional / payment_frequency * expected_df
        
        # Valor presente de la pata flotante
        floating_leg = notional * (1 - self._calculate_discount_factor(time_index, state_index, time_index + swap_tenor))
        
        # Valor del swap = pata flotante - pata fija
        return floating_leg - fixed_leg
    
    def _calculate_discount_factor(self, from_time_index, from_state_index, to_time):
        """
        Calcula el factor de descuento desde un nodo específico hasta un tiempo futuro
        """
        to_time_index = min(int(to_time / self.dt), self.time_steps)
        if from_time_index == to_time_index:
            return 1.0
        
        # Calcular el factor de descuento esperado
        expected_df = 0
        for j in range(to_time_index + 1):
            prob = self.binomial_probability(to_time_index - from_time_index, j - from_state_index, self.p)
            if 0 <= j <= to_time_index:
                expected_df += prob * np.exp(-self.rates[to_time_index, j] * (to_time_index - from_time_index) * self.dt)
        
        return expected_df


# Ejemplo de uso
def ejemplo_valoracion_swaption_bermuda():
    # Definir la curva de tipos de interés
    zero_rates = {
        0.5: 0.05,    # 5% a 6 meses
        1.0: 0.055,   # 5.5% a 1 año
        1.5: 0.06,    # 6% a 1.5 años
        2.0: 0.065,   # 6.5% a 2 años
        3.0: 0.07,    # 7% a 3 años
        5.0: 0.075,   # 7.5% a 5 años
        7.0: 0.08,    # 8% a 7 años
        10.0: 0.085   # 8.5% a 10 años
    }
    
    # Parámetros del modelo
    volatility = 0.20  # 20% volatilidad anualizada
    time_steps = 40
    
    # Crear el árbol de tipos de interés
    tree = BinomialInterestRateTree(zero_rates, volatility, time_steps)
    
    # Parámetros del swaption
    strike = 0.065  # Tasa fija del 6.5%
    swap_tenor = 5.0  # Swap de 5 años
    exercise_dates = [1.0, 2.0, 3.0]  # Fechas de ejercicio: años 1, 2, 3
    notional = 1000000  # Nominal de 1 millón
    
    # Valorar el swaption Bermuda
    swaption_value = tree.value_swaption_bermuda(strike, swap_tenor, exercise_dates, notional)
    print(f"Valor del swaption Bermuda: {swaption_value:.2f}")
    
    return swaption_value

# Ejecutar el ejemplo
if __name__ == "__main__":
    ejemplo_valoracion_swaption_bermuda()
