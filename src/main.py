from loader import load_models

MODELS = "models.json"

def loadModels():
    models = load_models(MODELS)
    if not models:
        print("Nenhum modelo foi carregado. Encerrando o programa.")
        return
    print("Estruturas carregadas em memória!")
    print(f"\nTotal de modelos carregados: {len(models)}\n" + "="*40)
    return models

def main():
    models = loadModels()



if __name__ == "__main__":
    main()