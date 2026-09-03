import sys
import tkinter as tk
from loader import load_models
from interface import App

def initialize_data(filepath: str):
    models = load_models(filepath)
    if not models:
        print("[Fatal] Nenhum modelo carregado de models.json.")
        sys.exit(1)
    print(f"[Sistema] {len(models)} modelos carregados com sucesso.")
    return models

def main():
    models_list = initialize_data("models.json")
    root = tk.Tk()
    app = App(root, models=models_list)
    root.mainloop()

if __name__ == "__main__":
    main()