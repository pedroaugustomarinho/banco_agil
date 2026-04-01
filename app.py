import os
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import logging
from langchain_core.messages import HumanMessage
from backend.graph import app_graph

# Configuração de Logs de Erro
logging.basicConfig(filename='logs/error.log', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

st.set_page_config(page_title="Banco Ágil - Atendimento", page_icon="🏦")
st.title("🏦 Banco Ágil - Assistente Virtual")

# Inicialização de Estado/Memória
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.agent_state = {
        "messages": [], 
        "cpf_autenticado": None, 
        "tentativas_auth": 0, 
        "agente_atual": "triagem",
        "atendimento_encerrado": False
    }

# Exibir histórico na tela
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Verificamos se a flag de encerramento é True no estado atual
encerrado = st.session_state.agent_state.get("atendimento_encerrado", False)

# O chat_input aceita um parâmetro 'disabled'
user_input = st.chat_input("Digite sua mensagem aqui...", disabled=encerrado)

if encerrado:
    st.info("Atendimento encerrado. Atualize a página para iniciar uma nova sessão.")

if user_input:
    # Mostra mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Prepara mensagem para o LangGraph
    st.session_state.agent_state["messages"].append(HumanMessage(content=user_input))

    try:
        # Invoca o Grafo
        config = {"configurable": {"thread_id": "sessao_unica"}}
        with st.spinner("Processando..."):
            result = app_graph.invoke(st.session_state.agent_state, config=config)
            
            # Atualiza o estado da sessão
            st.session_state.agent_state = result
            
            # LOOP DE FERRAMENTAS: Garante que todas as ferramentas acionadas pela IA sejam 
            # executadas no backend antes de exibir a resposta final para o usuário.
            while hasattr(result["messages"][-1], 'tool_calls') and result["messages"][-1].tool_calls:
                result = app_graph.invoke(result, config=config)
            
            # Atualiza o estado da sessão com a versão final (após as ferramentas)
            st.session_state.agent_state = result
            resposta_assistente = result["messages"][-1].content
            
            # Exibe resposta
            st.session_state.messages.append({"role": "assistant", "content": resposta_assistente})
            with st.chat_message("assistant"):
                st.markdown(resposta_assistente)

            # CORREÇÃO DO DELAY: Força o recarregamento da interface imediatamente se o estado mudou para encerrado
            if st.session_state.agent_state.get("atendimento_encerrado", False):
                st.rerun()

    except Exception as e:
        # Tratamento de exceção de API requerido pelo desafio
        logging.error(f"Erro na execução da API Groq/Grafo: {str(e)}")
        mensagem_erro = "Desculpe, nosso sistema está momentaneamente fora do ar, mas em breve retornamos."
        st.session_state.messages.append({"role": "assistant", "content": mensagem_erro})
        with st.chat_message("assistant"):
            st.error(mensagem_erro)