import socket
import threading
import time

# --- Constantes ---
PORTA_UDP = 9000
TEMPO_ANUNCIO = 15  # Segundos para anunciar rotas 
TEMPO_TIMEOUT = 35   # Segundos para considerar um vizinho morto 
MEU_IP = "192.168.1.1" # Você precisará descobrir isso dinamicamente ou configurar

# --- Estruturas de Dados ---
# Tabela de Roteamento: { "ip_destino": {"metrica": 1, "ip_saida": "192.x.x.x"} }
tabela_roteamento = {}

# Lista de Vizinhos: "ip_vizinho"
# Você vai ler isso do 'roteadores.txt'
vizinhos = ["192.168.1.2", "192.168.1.3"]

# Rastreamento de Timeout: { "ip_vizinho": tempo_da_ultima_mensagem }
vizinhos_ativos = {}

# Trava (Lock) para proteger o acesso à tabela de roteamento, 
# já que várias threads vão acessá-la.
lock_tabela = threading.Lock()

# --- Funções das Threads ---

def thread_ouvinte_udp():
    """
    Thread 1: Ouve a porta 9000 por qualquer mensagem UDP.
    """
    print(f"Ouvindo na porta {PORTA_UDP}...")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(('', PORTA_UDP)) # Ouve em todas as interfaces
        
        while True:
            dados, endereco = s.recvfrom(1024)
            ip_origem = endereco[0]
            mensagem = dados.decode('utf-8')
            
            print(f"Recebido de {ip_origem}: {mensagem}")
            
            # 1. Atualizar o tempo de atividade do vizinho que enviou
            with lock_tabela:
                vizinhos_ativos[ip_origem] = time.time()

            # 2. Processar a mensagem
            if mensagem.startswith('*'):
                ip = mensagem[1:]
                
                with lock_tabela:
                    tabela_roteamento[ip] = {"metrica": 1, "ip_saida": ip}

            elif mensagem.startswith('#'):
                # Parte 1: Anúncio de Rotas
                rotas = mensagem.split('#')[1:] # Ignorar o # inicial
                with lock_tabela:
                    for rota in rotas:
                        destino, metrica_str = rota.split('-')

                        if destino == MEU_IP:
                            continue  # Ignorar rotas para mim mesmo

                        metrica = int(metrica_str)
                        metrica_atual = tabela_roteamento.get(destino, {"metrica": float('inf')})["metrica"]
                        
                        nova_metrica = metrica + 1 
                        
                        if nova_metrica < metrica_atual:
                            tabela_roteamento[destino] = {
                                "metrica": nova_metrica,
                                "ip_saida": ip_origem
                            }
                            enviar_tabela_rotas(s)

            elif mensagem.startswith('!'):
                # Parte 2: Mensagem de texto [cite: 93, 101]
                try:
                    # Tenta quebrar a mensagem. maxsplit=2 garante que o texto
                    # da mensagem, mesmo se tiver ';', não seja quebrado.
                    partes = mensagem[1:].split(';', 2)
                    
                    if len(partes) != 3:
                        print(f"Recebida mensagem de texto mal formatada: {mensagem}")
                        continue

                    ip_origem_msg, ip_destino_msg, texto_msg = partes

                    # Verificar se a mensagem é para mim [cite: 96]
                    if ip_destino_msg == MEU_IP:
                        print("\n======================================")
                        print("MENSAGEM RECEBIDA (DESTINO FINAL)")
                        print(f"De: {ip_origem_msg}")
                        print(f"Para: {ip_destino_msg}")
                        print(f"Texto: {texto_msg}")
                        print("======================================\n")
                    
                    # Se não for para mim, rotear para o próximo 
                    else:
                        proximo_salto_ip = None
                        with lock_tabela:
                            if ip_destino_msg in tabela_roteamento:
                                proximo_salto_ip = tabela_roteamento[ip_destino_msg]["ip_saida"]
                        
                        if proximo_salto_ip:
                            print(f"Repassando mensagem de {ip_origem_msg} para {ip_destino_msg} via {proximo_salto_ip}...")
                            # Reenvia a mensagem original, inalterada, para o próximo salto
                            s.sendto(mensagem.encode('utf-8'), (proximo_salto_ip, PORTA_UDP))
                        else:
                            print(f"Mensagem de {ip_origem_msg} para {ip_destino_msg} DESCARTADA (sem rota)")

                except Exception as e:
                    print(f"Erro ao processar mensagem de texto: {e}")

def thread_anunciante_rotas():
    """
    Thread 2: A cada 15 segundos, envia a tabela de rotas para os vizinhos.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        while True:
            time.sleep(TEMPO_ANUNCIO)
            enviar_tabela_rotas(s)
            

def thread_monitor_timeout():
    """
    Thread 3: Verifica periodicamente se algum vizinho expirou (35s).
    """
    while True:
        time.sleep(5) # Verificar a cada 5 segundos, por exemplo
        agora = time.time()
        
        with lock_tabela:
            vizinhos_mortos = []
            for vizinho, ultimo_contato in vizinhos_ativos.items():
                if agora - ultimo_contato > TEMPO_TIMEOUT:
                    vizinhos_mortos.append(vizinho)
            
            if vizinhos_mortos:
                print(f"Vizinhos mortos detectados: {vizinhos_mortos}")
                
                # --- Início da Lógica de Remoção ---
                rotas_a_remover = []
                
                # Encontra todas as rotas que dependem (usam como saída) dos vizinhos mortos
                for destino, info in tabela_roteamento.items():
                    if info["ip_saida"] in vizinhos_mortos:
                        rotas_a_remover.append(destino)
                
                # Remove essas rotas da tabela
                for destino in rotas_a_remover:
                    print(f"Removendo rota para {destino} (via {tabela_roteamento[destino]['ip_saida']})")
                    del tabela_roteamento[destino]
                    
                # Remove os vizinhos mortos do rastreamento de atividade
                for vizinho in vizinhos_mortos:
                    if vizinho in vizinhos_ativos:
                        del vizinhos_ativos[vizinho]
                
                print(f"Tabela atualizada após remoção: {tabela_roteamento}")

def enviar_tabela_rotas(s):
    mensagem_rotas = ""
    with lock_tabela:

        # Construir a mensagem de rotas no formato "#ip-metrica#ip-metrica"
        for destino, info in tabela_roteamento.items():
            mensagem_rotas += f"#{destino}-{info['metrica']}"

    if mensagem_rotas:
        print("Enviando anúncio de rotas...")
        for vizinho in vizinhos:
            print(f"Enviando para {vizinho}: {mensagem_rotas}")
            s.sendto(mensagem_rotas.encode('utf-8'), (vizinho, PORTA_UDP))

# --- Função Principal (Inicialização) ---
def main():
    # 1. Ler roteadores.txt e popular 'vizinhos' e 'tabela_roteamento' inicial
    with open("roteadores.txt", 'r') as f:
        for linha in f:
            ip_vizinho = linha.strip().strip('"')
            vizinhos.append(ip_vizinho)
            tabela_roteamento[ip_vizinho] = {"metrica": 1, "ip_saida": ip_vizinho}
            vizinhos_ativos[ip_vizinho] = time.time()
    
    # 2. Iniciar as threads
    t_ouvinte = threading.Thread(target=thread_ouvinte_udp, daemon=True)
    t_anunciante = threading.Thread(target=thread_anunciante_rotas, daemon=True)
    t_monitor = threading.Thread(target=thread_monitor_timeout, daemon=True)
    
    t_ouvinte.start()
    t_anunciante.start()
    t_monitor.start()

    # 3. Enviar o "Anúncio de Roteador" (Mensagem 2) para os vizinhos
    mensagem_ola = f"*{MEU_IP}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for vizinho in vizinhos:
            s.sendto(mensagem_ola.encode('utf-8'), (vizinho, PORTA_UDP))
            
    print("Anúncio de entrada enviado.")
    
    # 4. Loop principal (Thread Principal) para a Parte 2: Envio de Mensagens
    print("\n--- Roteador Online ---")
    print("Digite 'tabela' para ver a tabela de roteamento.")
    print("Para enviar: digite 'IP_DESTINO;MENSAGEM_DE_TEXTO'")
    
    try:
        while True:
            # Bloqueia a thread principal esperando pela entrada do usuário
            entrada = input("> ")
            
            if entrada.lower() == 'tabela':
                with lock_tabela:
                    print("\n--- Tabela de Roteamento Atual ---")
                    for destino, info in tabela_roteamento.items():
                        print(f"Destino: {destino.ljust(15)} | Métrica: {info['metrica']} | Saída: {info['ip_saida']}")
                    print("----------------------------------\n")
                continue

            try:
                # Tenta dividir a entrada do usuário
                ip_destino, mensagem_texto = entrada.split(';', 1)
                
                if not ip_destino or not mensagem_texto:
                    raise ValueError("Formato inválido")

                # Formata a mensagem de texto completa [cite: 99, 100]
                mensagem_formatada = f"!{MEU_IP};{ip_destino};{mensagem_texto}"
                
                # Encontrar o próximo salto (IP de Saída)
                proximo_salto_ip = None
                with lock_tabela:
                    if ip_destino in tabela_roteamento:
                        proximo_salto_ip = tabela_roteamento[ip_destino]["ip_saida"]
                
                if proximo_salto_ip:
                    # Envia a mensagem para o próximo salto
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s_send:
                        s_send.sendto(mensagem_formatada.encode('utf-8'), (proximo_salto_ip, PORTA_UDP))
                    print(f"Mensagem enviada para {ip_destino} (via {proximo_salto_ip})")
                else:
                    print(f"Erro: Sem rota conhecida para {ip_destino}")

            except ValueError:
                print("Formato inválido. Use 'IP_DESTINO;MENSAGEM_DE_TEXTO'")
    
    except KeyboardInterrupt:
        print("\nDesligando roteador...")

if __name__ == "__main__":
    main()