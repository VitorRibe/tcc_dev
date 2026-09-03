import tkinter as tk
from tkinter import ttk
from utils.colors import Palette
from OpenGL.GL import *
from pyopengltk import OpenGLFrame


WIDTH = 1080
LENGTH = 720

class FrameFractalGL(OpenGLFrame):
    # Frame dedicado ao contexto OpenGL para renderização 3D
    def initgl(self):
        glClearColor(0.91, 0.91, 0.91, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])

    def redraw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

class App:
    def __init__(self, root, models=None):
        self.root = root
        self.root.title("Visualizador 3d")
        self.root.geometry(f"{WIDTH}x{LENGTH}")

        self.models_list = models if models else []
        self.selected_model = None 

        # self._load_menu()
        self._load_configs()
        right_container = tk.Frame(self.root, bg=Palette.BACKGROUND_NIGHT)
        right_container.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        
        self._load_footer(right_container)
        self._load_canvas(right_container)

    def _load_menu(self):
        menu_bar = tk.Menu(self.root)

        # Menu Arquivo
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Abrir", command=self.action_placeholder)
        file_menu.add_command(label="Sair", command=self.root.quit)
        menu_bar.add_cascade(label="Arquivo", menu=file_menu)

        # Menu Ajuda
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Sobre", command=self.action_placeholder)
        menu_bar.add_cascade(label="Ajuda", menu=help_menu)

        self.root.config(menu=menu_bar)

    def _load_footer(self, parent_frame):
        self.footer_frame = tk.Frame(parent_frame, bg=Palette.BACKGROUND, height=30)
        self.footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.footer_frame.pack_propagate(False) # Mantém a altura fixa
        self.footer_label = tk.Label(
            self.footer_frame, 
            text="Status: Nenhum modelo carregado.", 
            bg=Palette.BACKGROUND, 
            anchor="e",
            font=("Arial", 9)
        )
        self.footer_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    def _load_configs(self):
        # painel de configurações
        painel = tk.Frame(self.root, width=220, bg=Palette.BACKGROUND)
        painel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        painel.pack_propagate(False)
        tk.Label(painel, text="Configurações", font=("Arial", 12, "bold"), bg=Palette.BACKGROUND).pack(pady=15)

        # Escolha de modelo
        tk.Label(painel, text="Escolha um modelo:", bg=Palette.BACKGROUND).pack(pady=15, anchor='w')

        opcoes = [model.name for model in self.models_list]
        
        self.combo = ttk.Combobox(painel, values=opcoes, state="readonly")
        self.combo.pack(fill=tk.X, padx=10)

        btn_load = tk.Button(painel, text="Carregar Modelo", command=self.carregar_modelo_selecionado)
        btn_load.pack(padx=10, pady=5)

        # Botão de Ação
        btn_reload = tk.Button(painel, text="Atualizar Modelo")
        btn_reload.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

    def carregar_modelo_selecionado(self, event=None):
        nome_escolhido = self.combo.get()

        if not nome_escolhido:
            print("Nenhum modelo selecionado na lista.")
            return
        
        for model in self.models_list:
            if model.name == nome_escolhido:
                self.selected_model = model
                break

        if self.selected_model:
            # Atualiza o texto do rodapé com as informações do modelo
            info_texto = f"Ativo: {self.selected_model.name}  |  Axioma: {self.selected_model.axiom}  |  Iterações: {self.selected_model.iterations}"
            self.footer_label.config(text=info_texto)
            print(f"Modelo selecionado e salvo na variável: {self.selected_model.name}")

    def _load_canvas(self, parent_frame):
        canvas_frame = tk.Frame(parent_frame, bg=Palette.BACKGROUND_NIGHT)
        canvas_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

        self.fractal_gl = FrameFractalGL(canvas_frame)
        self.fractal_gl.pack(fill=tk.BOTH, expand=True)

    def action_placeholder(self):
        print("Ação de menu clicada.")