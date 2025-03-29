import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Lista para armazenar a trajetória
trajectory = []
fig, ax = plt.subplots()

def update_plot():
    """Atualiza o gráfico com a trajetória, sem os pontos."""
    if len(trajectory) < 2:
        return
    
    ax.clear()
    ax.set_title("Trajetória")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True)
    
    lons, lats = zip(*trajectory)
    ax.plot(lons, lats, 'b-', linewidth=2)  # Linha da trajetória sem pontos
    plt.draw()

def get_coordinates():
    """Obtém coordenadas do usuário e atualiza o gráfico."""
    try:
        latitude = entry_lat.get()
        longitude = entry_lon.get()
        
        if not latitude or not longitude:
            return
        
        lat, lon = float(latitude), float(longitude)
        
        # Apenas adiciona se for um novo ponto (evita duplicatas consecutivas)
        if not trajectory or (lat, lon) != trajectory[-1]:
            trajectory.append((lat, lon))
            update_plot()
    except ValueError:
        pass

def animate(i):
    """Função de animação para atualizar o gráfico periodicamente."""
    update_plot()

# Configuração da interface gráfica
root = tk.Tk()
root.title("Mapa de Satélite com Trajetória - Visualização Gráfica")

frame = tk.Frame(root)
frame.pack(pady=20)

tk.Label(frame, text="Latitude:").grid(row=0, column=0)
entry_lat = tk.Entry(frame)
entry_lat.grid(row=0, column=1)

tk.Label(frame, text="Longitude:").grid(row=1, column=0)
entry_lon = tk.Entry(frame)
entry_lon.grid(row=1, column=1)

btn_add = tk.Button(root, text="Adicionar Ponto", command=get_coordinates)
btn_add.pack(pady=10)

# Configuração do gráfico
ax.set_xlim(-180, 180)
ax.set_ylim(-90, 90)
ax.set_title("Trajetória do Aeromodelo")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.grid(True)
ani = animation.FuncAnimation(fig, animate, interval=500)

plt.show()
root.mainloop()
