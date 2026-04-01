# 🏦 Banco Ágil - Sistema Multi-Agentes de Atendimento

## 📖 Visão Geral do Projeto
Este projeto é a implementação de um sistema de atendimento ao cliente para o Banco Ágil, desenvolvido como solução para o Desafio Técnico de Desenvolvedor de Agentes de IA. O sistema utiliza uma arquitetura baseada em múltiplos agentes autônomos para gerenciar autenticação, consultas de crédito, entrevistas de reavaliação financeira e cotações de câmbio de forma fluida e segura.

## 🏗️ Arquitetura do Sistema e Manipulação de Dados
O sistema foi construído utilizando o ecossistema **LangChain** e **LangGraph** para orquestração de fluxo, tendo como motor de raciocínio o modelo **Llama 3** (via Groq API). A interface de testes foi desenvolvida em **Streamlit**.

* **Orquestração e Fluxo:** Um nó supervisor atua como roteador dinâmico. Ele avalia o histórico da conversa e as intenções do usuário, realizando transições implícitas entre os agentes modificando o estado global (`AgentState`). Para o cliente, a experiência é a de conversar com um único assistente versátil.
* **Memória e Estado:** O histórico conversacional e as variáveis de sessão (como `cpf_autenticado`) transitam pela máquina de estados do LangGraph, permitindo decisões contextualizadas e evitando repetições.
* **Manipulação de Dados:** O isolamento das operações de I/O ocorre no módulo `backend/data_handler.py`. As ferramentas (`tools.py`) acessam e atualizam arquivos `.csv` atuando como banco de dados (clientes, regras de score e registro de solicitações). O sistema conta com uma forte blindagem de limpeza de strings, regex e coerção de tipos via Pandas para garantir a resiliência contra formatações mistas.

## 🚀 Funcionalidades Implementadas
* **Agente de Triagem:** Recepciona e autentica o usuário (CPF e Data de Nascimento) consultando a base de dados, com limite de tentativas.
* **Agente de Crédito:** Restrito a usuários autenticados, consulta limites e registra pedidos de aumento no arquivo `solicitacoes_aumento_limite.csv`, informando aprovação ou rejeição baseada no score.
* **Agente de Entrevista de Crédito:** Conduz um formulário interativo de 5 passos para coletar dados financeiros e recalcula o score do cliente matematicamente, atualizando a base.
* **Agente de Câmbio:** Consulta a cotação do Dólar em tempo real conectando-se a uma API pública, sem necessidade de autenticação.
* **Encerramento Global:** Ferramenta dedicada para finalizar a execução e bloquear novas interações caso o usuário solicite o fim do atendimento.

## 🛠️ Escolhas Técnicas e Justificativas
* **LangGraph sobre abordagens sequenciais:** Escolhido pela capacidade nativa de gerenciar grafos cíclicos de estado, o que é vital para chatbots que precisam manter memória de longo prazo e transitar entre diferentes domínios sem perder o contexto da sessão.
* **Groq + Llama 3:** Adotados pela altíssima velocidade de inferência (TPS) proporcionada pelas LPUs da Groq e pela qualidade do modelo open-source Llama, garantindo respostas rápidas cruciais para a experiência em um chat bancário.
* **Pandas para Dados:** Utilizado para blindar a aplicação contra erros de encoding e separadores inconsistentes muito comuns no tratamento de arquivos CSV, cumprindo o requisito de tratamento resiliente de erros.

## 🧗 Desafios Enfrentados e Resoluções
* **Isolamento de Escopo e "Alucinação" de Ferramentas:** LLMs tendem a tentar resolver problemas sozinhos em vez de delegar para as ferramentas. Isso foi resolvido aplicando *Prompt Engineering* estrito (regras inegociáveis e diretrizes negativas) e o uso do método `.bind_tools()` exclusivo por nó, garantindo que nenhum agente invada a responsabilidade do outro.
* **Transição Silenciosa:** Evitar que a IA narrasse suas ações ("Vou te transferir...") exigiu ajustes de precedência no roteador (`supervisor_node`) para agir com base em palavras-chave e intenção, mascarando a troca de system prompts no backend.

## 💻 Tutorial de Execução e Testes

### 1. Preparação do Ambiente
```bash
git clone <url-do-seu-repositorio>
cd banco_agil
python -m venv venv
# No Windows: venv\Scripts\activate
# No Linux/Mac: source venv/bin/activate
pip install -r requirements.txt