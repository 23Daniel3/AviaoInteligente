import cv2
import numpy as np

# Caminho absoluto da imagem
image_path = 'src/main/resources/image.png'
image = cv2.imread(image_path)

if image is None:
    print(f"Erro: Imagem não encontrada! Verifique o caminho: {image_path}")
    exit()

# Converter para HSV
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# Faixas de cores ajustadas para detectar a falta de verde (áreas com baixa saturação e valor)
# Áreas sem vegetação, como solo exposto e desmatamento, geralmente possuem baixa saturação e valor
lower_no_green = np.array([0, 0, 50])  # Saturações muito baixas, com valor mais alto (áreas claras)
upper_no_green = np.array([179, 50, 150])  # Faixa de cor mais ampla para detectar falta de verde (tons acinzentados e marrons)

# Criar máscara para detectar áreas sem verde
mask_no_green = cv2.inRange(hsv, lower_no_green, upper_no_green)

# Suavizar a máscara para reduzir falsos positivos e detectar áreas mais amplas
kernel = np.ones((10, 10), np.uint8)
mask_no_green = cv2.morphologyEx(mask_no_green, cv2.MORPH_CLOSE, kernel)  # Fechar pequenos buracos
mask_no_green = cv2.morphologyEx(mask_no_green, cv2.MORPH_OPEN, kernel)  # Remover pequenos ruídos

# Aplicar suavização na imagem para detectar áreas maiores
smooth_image = cv2.GaussianBlur(image, (5, 5), 0)

# Encontrar os contornos das áreas detectadas
contours, _ = cv2.findContours(mask_no_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Desenhar contornos na imagem original
for contour in contours:
    if cv2.contourArea(contour) > 2000:  # Aumentar a área mínima para detectar apenas regiões maiores
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(image, "Falta de Verde (Desmatamento)", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

# Exibir a imagem processada
cv2.imshow('Detecção de Falta de Verde', image)
cv2.waitKey(0)
cv2.destroyAllWindows()
