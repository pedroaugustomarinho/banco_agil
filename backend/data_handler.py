import pandas as pd
import os
from datetime import datetime

CLIENTES_FILE = "data/clientes.csv"
SCORE_FILE = "data/score_limite.csv"
SOLICITACOES_FILE = "data/solicitacoes_aumento_limite.csv"

def autenticar_cliente(cpf: str, data_nasc: str) -> dict:
    try:
        df = pd.read_csv(CLIENTES_FILE, sep=';', dtype={'cpf': str}, encoding='latin-1')
        
        # 1. Remove qualquer linha que tenha CPF ou data vazios (mata os 'nan')
        df.dropna(subset=['cpf', 'data_nascimento'], inplace=True)
        
        # 2. Higienização: Tira espaços e garante o uso de barras (/) no lugar de traços (-)
        df['cpf'] = df['cpf'].astype(str).str.strip()
        df['data_nascimento'] = df['data_nascimento'].astype(str).str.strip().str.replace('-', '/')
        
        # 3. Limpa a entrada enviada pela IA
        cpf_busca = str(cpf).strip()
        data_busca = str(data_nasc).strip().replace('-', '/')
        
        # Faz a busca com os dados devidamente alinhados
        cliente = df[(df['cpf'] == cpf_busca) & (df['data_nascimento'] == data_busca)]
        
        if not cliente.empty:
            return cliente.iloc[0].to_dict()
        return None
    except Exception as e:
        raise RuntimeError(f"Erro ao acessar base de clientes: {e}")

def obter_limite_e_score(cpf: str) -> dict:
    try:
        df = pd.read_csv(CLIENTES_FILE, sep=';', dtype={'cpf': str}, encoding='latin-1')
        df.columns = df.columns.str.strip()
        df['cpf'] = df['cpf'].astype(str).str.strip()
        cpf_busca = str(cpf).strip()
        
        cliente = df[df['cpf'] == cpf_busca]
        if not cliente.empty:
            # Força a conversão para texto, troca a vírgula brasileira por ponto e converte para número real
            limite_str = str(cliente.iloc[0]['limite_atual']).replace(',', '.')
            score_str = str(cliente.iloc[0]['score']).replace(',', '.')
            
            return {
                "limite_atual": float(limite_str), 
                "score": int(float(score_str))
            }
        return None
    except Exception as e:
         raise RuntimeError(f"Erro ao acessar base de clientes: {e}")

def registrar_solicitacao(cpf: str, limite_atual: float, novo_limite: float, status: str):
    try:
        nova_linha = {
            "cpf_cliente": str(cpf).strip(),
            "data_hora_solicitacao": datetime.utcnow().isoformat() + "Z",
            "limite_atual": limite_atual,
            "novo_limite_solicitado": novo_limite,
            "status_pedido": status
        }
        
        # Lê o arquivo garantindo o separador correto e a limpeza do cabeçalho
        df = pd.read_csv(SOLICITACOES_FILE, sep=';', dtype={'cpf_cliente': str}, encoding='latin-1')
        df.columns = df.columns.str.strip()
        
        df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
        
        # CRÍTICO: Salva de volta usando sep=';' e latin-1 para manter o padrão e não corromper o arquivo para as próximas leituras
        df.to_csv(SOLICITACOES_FILE, sep=';', encoding='latin-1', index=False)
    except Exception as e:
        raise RuntimeError(f"Erro ao registrar solicitação: {e}")

def verificar_limite_por_score(score: int, valor_solicitado: float) -> bool:
    try:
        df = pd.read_csv(SCORE_FILE, sep=';', encoding='latin-1')
        if 'min_score' not in df.columns.str.strip():
            df = pd.read_csv(SCORE_FILE, sep=',', encoding='latin-1')
            
        df.columns = df.columns.str.strip()
        
        # Limpeza bruta: remove tabs (\t) e espaços, e troca vírgula por ponto
        for col in ['min_score', 'max_score', 'limite_permitido']:
            df[col] = df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
            # O errors='coerce' é a mágica que transforma qualquer lixo (\t\t) em NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # Removemos qualquer linha que tenha virado NaN (as linhas vazias/sujas)
        df.dropna(subset=['min_score', 'max_score', 'limite_permitido'], inplace=True)
        
        score_num = float(score)
        valor_num = float(valor_solicitado)
        
        faixa = df[(df['min_score'] <= score_num) & (df['max_score'] >= score_num)]
        if not faixa.empty:
            limite_permitido = float(faixa.iloc[0]['limite_permitido'])
            return valor_num <= limite_permitido
        return False
    except Exception as e:
        raise RuntimeError(f"Erro ao verificar score: {e}")
    
def atualizar_score(cpf: str, novo_score: int):
    try:
        df = pd.read_csv(CLIENTES_FILE, sep=';', dtype={'cpf': str}, encoding='latin-1')
        df.columns = df.columns.str.strip()
        
        # Limpa tabs e espaços invisíveis usando regex
        df['cpf'] = df['cpf'].astype(str).str.replace(r'\s+', '', regex=True)
        cpf_busca = str(cpf).replace(r'\s+', '').strip()
        
        if cpf_busca in df['cpf'].values:
            # Garante que o score salvo seja um número inteiro limpo
            df.loc[df['cpf'] == cpf_busca, 'score'] = int(float(novo_score))
            df.to_csv(CLIENTES_FILE, sep=';', encoding='latin-1', index=False)
    except Exception as e:
        raise RuntimeError(f"Erro ao atualizar score: {e}")