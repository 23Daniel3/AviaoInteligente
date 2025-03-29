import os
import sys
import numpy as np
import pyvista as pv
from scipy.spatial.transform import Rotation as R
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
from pyvistaqt import BackgroundPlotter

# Caminho do modelo CAD
modelo_path = "C:/Users/danie/Desktop/Programacao/Avião Inteligente/src/main/resources/modelo.obj"

# Verifica se o arquivo existe
if not os.path.exists(modelo_path):
    print(f"Erro: Arquivo {modelo_path} não encontrado!")
    sys.exit(1)

# Carregar o modelo
modelo_original = pv.read(modelo_path)
modelo = modelo_original.copy()

# Calcular centro do modelo
centroide = modelo.points.mean(axis=0)

# Criar visualizador PyVista
plotter = BackgroundPlotter()
plotter.add_mesh(modelo, color="white")

def rotacionar_modelo(yaw, pitch, roll):
    """ Aplica a rotação ao modelo. """
    global modelo

    modelo.points = modelo_original.points.copy()
    modelo.points -= centroide

    # Aplicar rotação
    rotacao = R.from_euler('zyx', [yaw, pitch, roll], degrees=True).as_matrix()
    modelo.points = modelo.points @ rotacao.T

    modelo.points += centroide
    plotter.update()

# Criar interface gráfica (Tkinter)
root = tk.Tk()
root.title("Dashboard de Monitoramento")

# Criar frames para CAD e gráfico
frame_cad = tk.Frame(root)
frame_cad.pack(side=tk.LEFT, padx=10, pady=10)

frame_grafico = tk.Frame(root)
frame_grafico.pack(side=tk.RIGHT, padx=10, pady=10)

# Entrada para rotação
tk.Label(frame_cad, text="Yaw:").pack()
entry_yaw = tk.Entry(frame_cad)
entry_yaw.pack()

tk.Label(frame_cad, text="Pitch:").pack()
entry_pitch = tk.Entry(frame_cad)
entry_pitch.pack()

tk.Label(frame_cad, text="Roll:").pack()
entry_roll = tk.Entry(frame_cad)
entry_roll.pack()

def aplicar_rotacao():
    """ Obtém valores e aplica rotação ao modelo. """
    try:
        yaw = float(entry_yaw.get())
        pitch = float(entry_pitch.get())
        roll = float(entry_roll.get())
        rotacionar_modelo(yaw, pitch, roll)
    except ValueError:
        pass

btn_rotacao = tk.Button(frame_cad, text="Aplicar Rotação", command=aplicar_rotacao)
btn_rotacao.pack(pady=5)

# Criar gráfico de trajetória
fig, ax = plt.subplots(figsize=(5, 4))
trajectory = []

def update_plot():
    """ Atualiza o gráfico da trajetória. """
    ax.clear()
    ax.set_title("Trajetória do Aeromodelo")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True)
    if trajectory:
        lons, lats = zip(*trajectory)
        ax.plot(lons, lats, 'b-', linewidth=2)
    canvas.draw()

def add_point():
    """ Adiciona novo ponto à trajetória. """
    try:
        lat = float(entry_lat.get())
        lon = float(entry_lon.get())
        if not trajectory or (lat, lon) != trajectory[-1]:
            trajectory.append((lat, lon))
            update_plot()
    except ValueError:
        pass

tk.Label(frame_grafico, text="Latitude:").pack()
entry_lat = tk.Entry(frame_grafico)
entry_lat.pack()

tk.Label(frame_grafico, text="Longitude:").pack()
entry_lon = tk.Entry(frame_grafico)
entry_lon.pack()

btn_add = tk.Button(frame_grafico, text="Adicionar Ponto", command=add_point)
btn_add.pack(pady=5)

canvas = FigureCanvasTkAgg(fig, master=frame_grafico)
canvas.get_tk_widget().pack()

# Loop principal do Tkinter
root.mainloop()
