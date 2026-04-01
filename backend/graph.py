import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.state import AgentState
from backend.tools import (
    tool_autenticar, tool_consultar_limite, tool_solicitar_aumento, 
    tool_calcular_atualizar_score, tool_consultar_cambio, tool_encerrar_atendimento
)
from backend.prompts import TRIAGEM_PROMPT, CREDITO_PROMPT, ENTREVISTA_PROMPT, CAMBIO_PROMPT

# Configuração da LLM
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# Bindings de ferramentas para cada persona
triage_llm = llm.bind_tools([tool_autenticar, tool_encerrar_atendimento])
credit_llm = llm.bind_tools([tool_consultar_limite, tool_solicitar_aumento, tool_encerrar_atendimento])
interview_llm = llm.bind_tools([tool_calcular_atualizar_score, tool_encerrar_atendimento])
exchange_llm = llm.bind_tools([tool_consultar_cambio, tool_encerrar_atendimento])

def supervisor_node(state: AgentState):
    """Atua como roteador principal do fluxo da conversa."""
    messages = state["messages"]
    last_msg_obj = messages[-1]
    
    # Busca a última mensagem da IA para dar contexto ao roteador
    ai_messages = [m for m in messages if m.type == "ai" and m.content]
    last_ai_msg = ai_messages[-1].content.lower() if ai_messages else ""
    
    # Busca CPF e Encerramento em uma única varredura
    for msg in reversed(messages):
        if not state.get("cpf_autenticado") and getattr(msg, "name", "") == "tool_autenticar" and "Autenticação bem-sucedida" in msg.content:
            import re
            match = re.search(r'\d{11}', msg.content)
            if match:
                state["cpf_autenticado"] = match.group(0)
                
        if getattr(msg, "name", "") == "tool_encerrar_atendimento":
            state["atendimento_encerrado"] = True

    current_agent = state.get("agente_atual", "triagem")
    tem_cpf = bool(state.get("cpf_autenticado"))
    
    if last_msg_obj.type == "human":
        last_msg = last_msg_obj.content.lower()
        
        # 1. Câmbio é livre
        if any(word in last_msg for word in ["câmbio", "dólar", "cotacao", "cotação"]):
            state["agente_atual"] = "cambio"
            
        # 2. Crédito (se tem CPF vai pra crédito; se não tem, volta pra triagem)
        elif any(word in last_msg for word in ["limite", "aumento", "crédito", "credito"]):
            state["agente_atual"] = "credito" if tem_cpf else "triagem"
            
        # 3. Entrevista (se tem CPF vai pra entrevista; se não tem, volta pra triagem)
        elif any(word in last_msg for word in ["entrevista", "score", "reavaliação", "reavaliacao", "perguntas", "perfil"]):
            state["agente_atual"] = "entrevista" if tem_cpf else "triagem"
            
        # 4. Concordância Implícita ("sim", "quero", "aceito") com Inteligência de Contexto
        elif any(word in last_msg.split() for word in ["sim", "quero", "aceito", "pode", "vamos", "ok", "claro"]):
            
            if current_agent == "credito":
                # Aceitou a entrevista sugerida pelo agente de crédito
                state["agente_atual"] = "entrevista"
                
            elif current_agent == "entrevista":
                # Só transfere de volta para o crédito se a IA acabou de oferecer o "limite" ou "reanálise".
                # (Isso impede que um "sim" para a pergunta de dívidas quebre a entrevista).
                if "reanálise" in last_ai_msg or "limite" in last_ai_msg:
                    state["agente_atual"] = "credito"
                    
        # 5. Fallback Implacável: Se não achou palavras de Câmbio e não tem CPF, VOLTA PRA TRIAGEM!
        elif not tem_cpf:
            state["agente_atual"] = "triagem"
            
        # Registra tentativas de erro de login
        if "falha na autenticação" in last_msg:
            state["tentativas_auth"] = state.get("tentativas_auth", 0) + 1
            
    return state

def node_executor(state: AgentState, llm_bound, prompt: str):
    """Executa o nó da LLM injetando o contexto do sistema e o CPF se autenticado."""
    messages = state["messages"]
    cpf = state.get("cpf_autenticado", "Desconhecido")
    system_msg = SystemMessage(content=prompt + f"\n\nContexto: CPF do cliente autenticado = {cpf}")
    
    response = llm_bound.invoke([system_msg] + messages)
    
    # Atualiza CPF no estado se a ferramenta de auth foi bem sucedida
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "tool_autenticar":
                # O state passará a ter o CPF assim que a tool rodar e retornar sucesso
                pass
                
    return {"messages": [response]}

# Funções wrappers para os nós do grafo
def node_triagem(state: AgentState): return node_executor(state, triage_llm, TRIAGEM_PROMPT)
def node_credito(state: AgentState): return node_executor(state, credit_llm, CREDITO_PROMPT)
def node_entrevista(state: AgentState): return node_executor(state, interview_llm, ENTREVISTA_PROMPT)
def node_cambio(state: AgentState): return node_executor(state, exchange_llm, CAMBIO_PROMPT)

def routing_logic(state: AgentState):
    if state.get("tentativas_auth", 0) >= 3:
        return END
    
    last_message = state["messages"][-1]
    #Checando se o estado é encerrar atendimento
    if getattr(last_message, "tool_calls", None):
            if last_message.tool_calls[0]["name"] == "tool_encerrar_atendimento":
                # Retorna para o toolnode do agente atual
                agent = state.get("agente_atual", "triagem")
                if agent == "triagem": return "triage_tools"
                if agent == "credito": return "credit_tools"
                if agent == "entrevista": return "interview_tools"
                if agent == "cambio": return "exchange_tools"

    # Se a LLM decidiu chamar uma ferramenta, roteia para o ToolNode adequado
    if getattr(last_message, "tool_calls", None):
        if last_message.tool_calls[0]["name"] == "tool_autenticar": return "triage_tools"
        if last_message.tool_calls[0]["name"] in ["tool_consultar_limite", "tool_solicitar_aumento"]: return "credit_tools"
        if last_message.tool_calls[0]["name"] == "tool_calcular_atualizar_score": return "interview_tools"
        if last_message.tool_calls[0]["name"] == "tool_consultar_cambio": return "exchange_tools"

    agent = state.get("agente_atual", "triagem")
    if agent == "cambio": return "cambio"
    if agent == "credito": return "credito"
    if agent == "entrevista": return "entrevista"
    return "triagem"

# Construção do Grafo
workflow = StateGraph(AgentState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("triagem", node_triagem)
workflow.add_node("credito", node_credito)
workflow.add_node("entrevista", node_entrevista)
workflow.add_node("cambio", node_cambio)

# Adicionando nós de ferramentas
workflow.add_node("triage_tools", ToolNode([tool_autenticar, tool_encerrar_atendimento]))
workflow.add_node("credit_tools", ToolNode([tool_consultar_limite, tool_solicitar_aumento, tool_encerrar_atendimento]))
workflow.add_node("interview_tools", ToolNode([tool_calcular_atualizar_score, tool_encerrar_atendimento]))
workflow.add_node("exchange_tools", ToolNode([tool_consultar_cambio, tool_encerrar_atendimento]))
workflow.set_entry_point("supervisor")

workflow.add_conditional_edges("supervisor", routing_logic)

# Retorno das ferramentas volta para o supervisor para reavaliar o estado
workflow.add_edge("triage_tools", "supervisor")
workflow.add_edge("credit_tools", "supervisor")
workflow.add_edge("interview_tools", "supervisor")
workflow.add_edge("exchange_tools", "supervisor")

# Retorno dos agentes de volta ao cliente (final da iteração, esperando novo HumanMessage)
workflow.add_edge("triagem", END)
workflow.add_edge("credito", END)
workflow.add_edge("entrevista", END)
workflow.add_edge("cambio", END)

# Compilação com suporte nativo a memória via threading base do LangGraph (ThreadSaver seria ideal, mas simplificaremos via frontend state)
app_graph = workflow.compile()