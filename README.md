# Aeromodelo Inteligente

## Descrição
Este projeto consiste no desenvolvimento de um **aeromodelo inteligente** equipado com sensores e conectividade Wi-Fi para controle remoto e monitoramento em tempo real. As principais funcionalidades incluem:

- **Visualização do ambiente por uma câmera do aeromodelo integrando detecção de objetos com yolov8** Para detecção de áreas com desmatamento e queimadas.
- **Visualização CAD do modelo em tempo real** com base nos dados do giroscópio.
- **Visualização da trajetória do aeromodelo** utilizando dados do GPS.
- **Comunicação por Wi-Fi**, permitindo controle remoto via WebSocket.
- **Integração com um controle Xbox** para acionar funções do sistema.
- **Leitura de botões via Wi-Fi**, permitindo monitoramento remoto de comandos.

## Tecnologias Utilizadas
- **ESP32** como microcontrolador principal.
- **WebSockets** para comunicação em tempo real.
- **Python** para interface e controle.
- **Pygame** para leitura do controle Xbox.
- **Sensores de giroscópio e GPS** para aquisição de dados de movimento e trajetória.

## Controle via Python e Controle Xbox
1. Uso de um código modular que permite uma fácil configuração com os controles para o aeromodelo.

## Visualização de Dados
- **Dados do giroscópio**: Atualizam o modelo CAD do aeromodelo em tempo real.
- **Dados do GPS**: Plotam a trajetória do aeromodelo em um mapa interativo.
- **Dados da IA**: São mostrados dados pela detecão de objetos com visão computacional com foco na detecção de áreas desmatadas e queimadas.

## Contribuição
Sinta-se à vontade para sugerir melhorias abrindo uma issue neste repositório.
