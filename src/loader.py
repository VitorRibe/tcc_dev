"""
Carrega e salva modelos de estruturas a partir de fontes externas.
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
    """Lê os modelos do JSON."""
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

def save_model(filepath: str, new_model: GrammarModel):
    """Salva um novo modelo validado no arquivo JSON existente."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {"models": []}
    
    data["models"].append({
        "name": new_model.name,
        "axiom": new_model.axiom,
        "iterations": new_model.iterations,
        "angle": new_model.angle,
        "rules": new_model.rules
    })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)