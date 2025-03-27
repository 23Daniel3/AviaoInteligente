package aviao;

import java.io.*;

public class Main {
    public static void main(String[] args) {
        try {
            // Definir o interpretador Python (usar ambiente virtual se necessário)
            String pythonExecutable = "python";  // Ou "venv/Scripts/python" se estiver usando venv
            String scriptPath = "C:/Users/danie/Desktop/Programacao/Avião Inteligente/app/src/main/resources/visualizer.py";
            
            // Criar o processo para rodar o script Python
            ProcessBuilder pb = new ProcessBuilder(pythonExecutable, scriptPath);
            pb.redirectErrorStream(true);
            Process process = pb.start();

            // Criar os fluxos de comunicação com o processo Python
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(process.getOutputStream()));

            // Thread para ler a saída do Python e exibi-la no console Java
            new Thread(() -> {
                String line;
                try {
                    while ((line = reader.readLine()) != null) {
                        System.out.println(line);
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }).start();

            // Loop para entrada do usuário
            BufferedReader userInput = new BufferedReader(new InputStreamReader(System.in));
            while (true) {
                System.out.print("Digite Yaw, Pitch e Roll (ex: 30 15 -10) ou 'exit' para sair: ");
                String input = userInput.readLine();
                if (input.equalsIgnoreCase("exit")) {
                    writer.write("exit\n");
                    writer.flush();
                    break;
                }

                // Enviar dados para o Python
                writer.write(input + "\n");
                writer.flush();
            }

            // Aguardar o término do processo Python
            process.waitFor();
            System.out.println("Python finalizado.");

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
