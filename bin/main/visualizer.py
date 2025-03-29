import pyvista as pv
import numpy as np
import os
import sys
from scipy.spatial.transform import Rotation as R  # Para cálculos de rotação

# Caminho do modelo CAD
modelo_path = "C:/Users/danie/Desktop/Programacao/Avião Inteligente/src/main/resources/modelo.obj"

# Verifique se o arquivo existe
if not os.path.exists(modelo_path):
    print(f"Erro: Arquivo {modelo_path} não encontrado!")
    sys.exit(1)

# Carregar o modelo
modelo_original = pv.read(modelo_path)  # Mantemos o modelo original
modelo = modelo_original.copy()  # Criamos uma cópia para manipulação

# Verifica se o modelo foi carregado corretamente
if modelo.n_points == 0:
    print("Erro: Modelo inválido!")
    sys.exit(1)

print("Modelo carregado com sucesso!")

# Calcular o centro do modelo
centroide = modelo.points.mean(axis=0)

# Criar a visualização
plotter = pv.Plotter()
plotter.add_mesh(modelo, color="white")  # Cor do modelo
plotter.show(interactive_update=True)  # Inicializa sem bloquear o terminal

def rotacionar_modelo(yaw, pitch, roll):
    """ Aplica a rotação absoluta ao modelo em torno do seu centro """
    global modelo

    # Restaurar modelo à posição original antes de aplicar nova rotação
    modelo.points = modelo_original.points.copy()

    # Deslocar o modelo para que o centro fique na origem
    modelo.points -= centroide

    # Criar matriz de rotação absoluta (ordem Yaw -> Pitch -> Roll)
    rotacao = R.from_euler('zyx', [yaw, pitch, roll], degrees=True).as_matrix()

    # Aplicar rotação ao modelo
    modelo.points = modelo.points @ rotacao.T  # Multiplicação da matriz de rotação

    # Retornar o modelo para a posição original
    modelo.points += centroide

    plotter.update()  # Atualizar a renderização

# Loop para receber os valores de Yaw, Pitch e Roll do Java
while True:
    try:
        entrada = input("Digite Yaw, Pitch e Roll ou 'exit' para sair: ").strip()
        if entrada.lower() == "exit" or entrada.lower() == "sair" or entrada.lower() == "sai":
            break

        yaw, pitch, roll = map(float, entrada.split())
        rotacionar_modelo(yaw, pitch, roll)

    except Exception as e:
        print(f"Erro: {e}")

print("Programa finalizado.")
plotter.close()  # Fecha a janela corretamente
