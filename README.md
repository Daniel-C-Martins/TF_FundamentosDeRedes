# Simulação de Roteador - Protocolo de Vetor de Distância

Este projeto implementa uma simulação de roteador em **Python**, capaz de trocar tabelas de roteamento dinamicamente com vizinhos e encaminhar mensagens de texto através da rede. A aplicação utiliza **Sockets UDP** para comunicação e **Multithreading** para gerenciar o envio, recebimento e monitoramento de rotas simultaneamente.

## 🎯 Funcionalidades

O projeto foi dividido em dois módulos principais:

### 1. Protocolo de Roteamento (Camada de Controle)
* **Descoberta de Vizinhos:** Leitura de arquivo de configuração (`roteadores.txt`) e anúncio automático ao entrar na rede (Hello Message).
* **Algoritmo de Vetor de Distância:**
    * Gerenciamento de tabela de roteamento (Destino, Métrica, IP de Saída).
    * Atualização de rotas baseada em menor métrica.
    * Incremento de métrica ao receber anúncios de vizinhos.
* **Updates Periódicos:** Envio da tabela de roteamento para vizinhos a cada **15 segundos**.
* **Tolerância a Falhas:** Detecção de vizinhos inativos (timeout) após **35 segundos** de silêncio, removendo rotas dependentes.

### 2. Troca de Mensagens (Camada de Dados)
* **Encaminhamento de Pacotes:** Roteamento de mensagens de texto (`string`) baseando-se na tabela de rotas construída dinamicamente.
* **Hop-by-Hop:** Se o roteador não for o destino final, ele repassa a mensagem para o próximo salto (*Next Hop*) definido na tabela.

## 🛠️ Arquitetura da Solução

Para resolver o problema da concorrência entre ouvir mensagens, enviar anúncios periódicos e monitorar timeouts, a solução foi arquitetada utilizando **3 Threads** concorrentes e um mecanismo de **Lock (Mutex)** para garantir a integridade dos dados.

### Diagrama de Threads
1.  **Thread Ouvinte (`thread_ouvinte_udp`):** Fica em loop infinito escutando a porta **9000**. Processa três tipos de pacotes:
    * `*IP`: Novos vizinhos entrando na rede.
    * `#IP-Metrica`: Atualizações de tabela de roteamento.
    * `!Origem;Destino;Msg`: Mensagens de texto para roteamento.
2.  **Thread Anunciante (`thread_anunciante_rotas`):** Responsável por disseminar a tabela local para os vizinhos a cada 15 segundos.
3.  **Thread Monitor (`thread_monitor_timeout`):** Verifica periodicamente a lista de vizinhos ativos. Se um vizinho não enviar dados por 35 segundos, ele é marcado como inativo e as rotas associadas são removidas.

### Decisões Técnicas
* **Thread Safety:** O uso de `threading.Lock()` (`lock_tabela`) protege a leitura e escrita na tabela de roteamento, prevenindo *Race Conditions* quando uma thread tenta ler a tabela para anunciar enquanto outra tenta atualizá-la com novos dados recebidos.
* **Split Horizon:** Implementado na função de envio para evitar loops de roteamento. O roteador não anuncia uma rota de volta para o vizinho que a ensinou.
* **Triggered Updates:** Além do envio periódico, o roteador envia atualizações imediatas sempre que uma mudança significativa ocorre na tabela (adição ou remoção de rota).

## 🚀 Como Executar

1.  **Configuração:**
    Crie um arquivo `roteadores.txt` no mesmo diretório, listando os IPs dos vizinhos (um por linha):
    ```text
    192.168.1.2
    192.168.1.3
    ```

2.  **Execução:**
    ```bash
    python Roteador.py
    ```
    *Nota: É necessário configurar a variável `MEU_IP` no código para corresponder ao IP da máquina atual.*

3.  **Comandos (Console Interativo):**
    * `tabela`: Exibe a tabela de roteamento atual.
    * `IP_DESTINO;MENSAGEM`: Envia uma mensagem de texto para outro roteador na rede.

## 📋 Especificação do Protocolo

O sistema utiliza mensagens formatadas em string pura sobre UDP na porta 9000:

| Tipo | Formato | Exemplo |
| :--- | :--- | :--- |
| **Anúncio de Rota** | `#IP-Metrica` | `#192.168.0.5-2` |
| **Hello (Entrada)** | `*IP` | `*192.168.0.1` |
| **Mensagem Texto** | `!Origem;Destino;Texto` | `!10.0.0.1;10.0.0.5;Olá` |

---
*Desenvolvido como parte da disciplina de Redes de Computadores.*
