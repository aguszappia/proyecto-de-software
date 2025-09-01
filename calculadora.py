
def calcular (num1, num2, operacion):
    if (operacion == '*'):
        return multiplicacion(num1,num2)
    elif operacion == '-':
        return resta(num1, num2)
    elif operacion == '+':
        return sumar(num1, num2)
    return none

def resta (num1,num2):
    return num1-num2
    
def sumar(num1, num2):
    return num1 + num2

def multiplicacion(num1, num2):
    return num1*num2