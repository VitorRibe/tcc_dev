from loader import load_models
import tkinter as tk
from interface import App


def loadModels():
    models = load_models()
    if not models:
        print("Nenhum modelo foi carregado. Encerrando o programa.")
        return
    print("Estruturas carregadas em memória!")
    print(f"\nTotal de modelos carregados: {len(models)}\n" + "="*40)
    return models

def main():
    models = loadModels()

    # interface gráfica
    root = tk.Tk()
    app = App(root, models)
    root.mainloop()

if __name__ == "__main__":
    main()