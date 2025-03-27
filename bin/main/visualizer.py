import open3d as o3d
import numpy as np
import os
import sys

# Caminho do modelo CAD
modelo_path = "C:/Users/danie/Desktop/Programacao/Avião Inteligente/app/src/main/resources/modelo.obj"  # Substitua pelo caminho correto do seu arquivo

# Verifique se o arquivo realmente existe
if not os.path.exists(modelo_path):
    print(f"Erro: Arquivo {modelo_path} não encontrado!")
    sys.exit(1)

# Carregar o modelo
modelo = o3d.io.read_triangle_mesh(modelo_path)

# Verifica se o modelo foi carregado corretamente
if modelo.is_empty():
    print("Erro: Modelo inválido!")
    sys.exit(1)

print("Modelo carregado com sucesso!")
modelo.paint_uniform_color([0.5, 0.5, 0.5])  # Cor cinza do modelo

# Inicializar a visualização
vis = o3d.visualization.Visualizer()
vis.create_window("Simulação de Rotação", width=800, height=600)
vis.add_geometry(modelo)
vis.poll_events()
vis.update_renderer()

def rotacionar_modelo(yaw, pitch, roll):
    yaw_rad = np.radians(yaw)
    pitch_rad = np.radians(pitch)
    roll_rad = np.radians(roll)

    R_yaw = modelo.get_rotation_matrix_from_xyz((0, 0, yaw_rad))  
    R_pitch = modelo.get_rotation_matrix_from_xyz((pitch_rad, 0, 0))  
    R_roll = modelo.get_rotation_matrix_from_xyz((0, roll_rad, 0))  

    modelo.rotate(R_yaw, center=(0, 0, 0))
    modelo.rotate(R_pitch, center=(0, 0, 0))
    modelo.rotate(R_roll, center=(0, 0, 0))

    vis.update_geometry(modelo)
    vis.poll_events()
    vis.update_renderer()

# Loop para receber os valores de Yaw, Pitch e Roll do Java
while True:
    try:
        entrada = input().strip()  # Lê os valores enviados pelo Java
        if entrada.lower() == "exit":
            break

        yaw, pitch, roll = map(float, entrada.split())
        rotacionar_modelo(yaw, pitch, roll)

    except Exception as e:
        print(f"Erro: {e}")

vis.destroy_window()
print("Programa finalizado.")
