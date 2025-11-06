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
vizinhos = ["192.168.1.2", "192.168.1.3"] # Exemplo

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
                # Mensagem 2: Anúncio de roteador [cite: 37]
                # Lógica para adicionar/atualizar vizinho (Métrica 1)
                pass
            
            elif mensagem.startswith('#'):
                # Mensagem 1: Anúncio de rotas [cite: 26]
                # Lógica de parse e atualização da tabela (regras 11, 13, 15)
                pass

            elif mensagem.startswith('!'):
                # Parte 2: Mensagem de texto [cite: 93, 101]
                # Lógica para verificar se é para mim ou para repassar [cite: 96, 97]
                pass

def thread_anunciante_rotas():
    """
    Thread 2: A cada 15 segundos, envia a tabela de rotas para os vizinhos.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        while True:
            time.sleep(TEMPO_ANUNCIO)
            
            mensagem_rotas = ""
            with lock_tabela:
                # Construir a mensagem de rotas no formato "#ip-metrica#ip-metrica..." [cite: 31, 32]
                # Lembre-se: não incluir rotas para si mesmo [cite: 36]
                for destino, info in tabela_roteamento.items():
                    mensagem_rotas += f"#{destino}-{info['metrica']}"
            
            if mensagem_rotas:
                print("Enviando anúncio de rotas...")
                for vizinho in vizinhos:
                    s.sendto(mensagem_rotas.encode('utf-8'), (vizinho, PORTA_UDP))

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
                # Lógica para remover rotas que passam por esses vizinhos 
                # ...
                pass

# --- Função Principal (Inicialização) ---
def main():
    # 1. Ler roteadores.txt e popular 'vizinhos' e 'tabela_roteamento' inicial
    # ...
    
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
    try:
        while True:
            # Aqui você implementa a lógica para o usuário digitar
            # o IP destino e a mensagem de texto
            time.sleep(1) # Apenas para não sobrecarregar
            pass
    
    except KeyboardInterrupt:
        print("\nDesligando roteador...")

if __name__ == "__main__":
    main()