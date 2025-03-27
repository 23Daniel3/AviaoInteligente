import folium
import tkinter as tk
from io import BytesIO
from PIL import Image, ImageTk
import requests

# Lista para armazenar a trajetória
trajectory = []

# Configuração da interface gráfica
root = tk.Tk()
root.title("Visualização de Satélite")
canvas = tk.Canvas(root, width=600, height=600)
canvas.pack()

def get_satellite_image(lat, lon, zoom=15):
    """Obtém uma imagem de satélite do serviço ESRI World Imagery."""
    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{int(lat)}/{int(lon)}"
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        return img
    else:
        raise Exception("Falha ao obter a imagem de satélite")

def update_map():
    """Atualiza a exibição do mapa na interface gráfica."""
    if not trajectory:
        return
    
    lat, lon = trajectory[-1]
    try:
        img = get_satellite_image(lat, lon)
        img = img.resize((600, 600))  # Ajusta o tamanho
        img_tk = ImageTk.PhotoImage(img)
        canvas.create_image(300, 300, image=img_tk)
        canvas.image = img_tk  # Mantém referência para evitar garbage collection
    except Exception as e:
        print(f"Erro ao carregar imagem: {e}")

def show_satellite_view():
    while True:
        try:
            latitude = input("Digite a latitude (ou 'sair' para encerrar): ")
            if latitude.lower() == 'sair':
                break
            longitude = input("Digite a longitude: ")
            
            latitude, longitude = float(latitude), float(longitude)
            trajectory.append((latitude, longitude))
            update_map()
        except ValueError:
            print("Entrada inválida. Certifique-se de inserir números para latitude e longitude.")
        except Exception as e:
            print(f"Ocorreu um erro: {e}")
    
    root.mainloop()

if __name__ == "__main__":
    show_satellite_view()