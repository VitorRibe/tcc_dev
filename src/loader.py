import json
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class GrammarModel:
    name: str
    axiom: str
    iterations: int
    rules: Dict[str, str]

def load_models(filepath: str) -> List[GrammarModel]:
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
    except FileNotFoundError:
         print(f"Erro: O arquivo {filepath} não foi encontrado.")
         return []
    except json.JSONDecodeError:
         print(f"Erro: O arquivo {filepath} não possui um formato JSON válido.")
         return []
    except Exception as e:
         print(f"Erro inesperado ao ler o arquivo: {e}")
         return []    

    print("Estruturas carregadas em memória!")

    try:
        return [
            GrammarModel(
                name=item["name"],
                axiom=item["axiom"],
                iterations=item["iterations"],
                rules=item["rules"]
            )
            for item in data.get("models", [])
        ]
    except KeyError as e:
        print(f"Erro: Estrutura do JSON inválida. Campo obrigatório ausente: {e}")
        return []

if __name__ == "__main__":
    models = load_models("models.json")