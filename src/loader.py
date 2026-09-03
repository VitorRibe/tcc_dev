"""
Carrega para a memória os modelos de estruturas a partir de fontes externas.
"""
import json
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class GrammarModel:
    name: str
    axiom: str
    iterations: int
    angle: float
    rules: Dict[str, str]

def load_models(filepath: str) -> List[GrammarModel]:
    """
    Carrega modelos de gramática de um arquivo JSON.
    Recebe o filepath como injeção de dependência.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"[Erro] O arquivo '{filepath}' não foi encontrado.")
        return []
    except json.JSONDecodeError:
        print(f"[Erro] O arquivo '{filepath}' não possui um formato JSON válido.")
        return []
    except Exception as e:
        print(f"[Erro] Falha inesperada ao ler o arquivo: {e}")
        return []
    
    try:
        return [
            GrammarModel(
                name=item["name"],
                axiom=item["axiom"],
                iterations=item["iterations"],
                angle=float(item.get("angle", 90.0)),
                rules=item["rules"]
            )
            for item in data.get("models", [])
        ]
    except KeyError as e:
        print(f"[Erro] Estrutura do JSON inválida. Campo obrigatório ausente: {e}")
        return []