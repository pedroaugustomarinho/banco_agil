from typing import Annotated, TypedDict, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cpf_autenticado: str
    tentativas_auth: int
    agente_atual: str
    atendimento_encerrado: bool