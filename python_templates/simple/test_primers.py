# PoC con codeGPT + Qwen2.5-coder-7B
def es_primo(num):
    if num <= 1:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True

def numeros_primos_menores_que_100():
    primos = []
    for numero in range(2, 100):
        if es_primo(numero):
            primos.append(numero)
    return primos

print(numeros_primos_menores_que_100())