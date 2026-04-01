from langchain_core.tools import tool
import requests
from backend.data_handler import (
    autenticar_cliente, obter_limite_e_score, 
    registrar_solicitacao, verificar_limite_por_score, atualizar_score
)

@tool
def tool_autenticar(cpf: str, data_nasc: str) -> str:
    """Autentica o usuário validando seu CPF e data de nascimento (DD/MM/YYYY)."""
    cliente = autenticar_cliente(cpf, data_nasc)
    if cliente:
        return f"Autenticação bem-sucedida para o CPF {cpf}. Nome: {cliente['nome']}."
    return "Falha na autenticação. Dados incorretos."

@tool
def tool_consultar_limite(cpf: str) -> str:
    """Consulta o limite atual e o score do cliente pelo CPF."""
    dados = obter_limite_e_score(cpf)
    if dados:
        return f"Limite atual: R${dados['limite_atual']}. Score: {dados['score']}."
    return "Cliente não encontrado."

@tool
def tool_solicitar_aumento(cpf: str, novo_limite: float) -> str:
    """Processa um pedido de aumento de limite."""
    dados = obter_limite_e_score(cpf)
    if not dados:
        return "Erro: Cliente não encontrado."
    
    limite_atual = dados['limite_atual']
    score_atual = dados['score']
    
    aprovado = verificar_limite_por_score(score_atual, novo_limite)
    status = 'aprovado' if aprovado else 'rejeitado'
    
    registrar_solicitacao(cpf, limite_atual, novo_limite, status)
    return f"Solicitação {status}. O novo limite solicitado foi R${novo_limite}."

@tool
def tool_calcular_atualizar_score(cpf: str, renda: float, despesas: float, tipo_emprego: str, num_dependentes: str, tem_dividas: str) -> str:
    """Calcula e atualiza o score de crédito com base na entrevista financeira."""
    peso_renda = 30
    peso_emprego = {"formal": 300, "autônomo": 200, "desempregado": 0}
    peso_dependentes = {"0": 100, "1": 80, "2": 60, "3+": 30}
    peso_dividas = {"sim": -100, "não": 100}
    
    # Tratamento básico de chaves
    tipo_emprego = tipo_emprego.lower()
    tem_dividas = tem_dividas.lower()
    num_dependentes = str(num_dependentes) if str(num_dependentes) in ["0", "1", "2"] else "3+"

    score = (
        (renda / (despesas + 1)) * peso_renda +
        peso_emprego.get(tipo_emprego, 0) +
        peso_dependentes.get(num_dependentes, 30) +
        peso_dividas.get(tem_dividas, -100)
    )
    score_final = max(0, min(1000, int(score))) # Garante entre 0 e 1000
    
    atualizar_score(cpf, score_final)
    return f"Novo score calculado e atualizado: {score_final}."

@tool
def tool_consultar_cambio(moeda: str = "USD") -> str:
    """Consulta a cotação atual de uma moeda em relação ao BRL usando API pública."""
    try:
        response = requests.get(f"https://economia.awesomeapi.com.br/last/{moeda}-BRL")
        dados = response.json()
        cotacao = float(dados[f'{moeda}BRL']['bid'])
        return f"A cotação atual do {moeda} é R$ {cotacao:.2f}."
    except Exception as e:
        return f"Não foi possível consultar a cotação no momento."
    
@tool
def tool_encerrar_atendimento() -> str:
    """Acionada OBRIGATORIAMENTE quando o usuário solicitar o fim da conversa, agradecer encerrando ou se despedir."""
    return "ATENDIMENTO_ENCERRADO"