import tkinter as tk
from tkinter import ttk
import numpy as np
from OpenGL.GL import *
from pyopengltk import OpenGLFrame
from utils.colors import Palette
from motor_lsystem import MotorLSystem

WIDTH = 1080
LENGTH = 720

class FrameFractalGL(OpenGLFrame):
    """Viewport OpenGL acoplada ao Tkinter via VBO dinâmico."""
    def initgl(self):
        glClearColor(0.17, 0.16, 0.16, 1.0)
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        glEnableClientState(GL_VERTEX_ARRAY)
        self.vbo_vertice = glGenBuffers(1)
        self.num_vertices = 0

        # Controle de Câmera 2D (Pan/Zoom)
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = -200.0
        self.last_x = 0
        self.last_y = 0

        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<MouseWheel>", self._on_zoom)
        self.bind("<Button-4>", lambda e: self._zoom_step(1.1))
        self.bind("<Button-5>", lambda e: self._zoom_step(1 / 1.1))

    def _on_click(self, event):
        self.last_x = event.x
        self.last_y = event.y

    def _on_drag(self, event):
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        self.offset_x += dx / self.zoom
        self.offset_y -= dy / self.zoom
        self.last_x = event.x
        self.last_y = event.y
        self.tkExpose(None)

    def _zoom_step(self, factor):
        self.zoom = max(0.01, min(50.0, self.zoom * factor))
        self.tkExpose(None)

    def _on_zoom(self, event):
        factor = 1.1 if event.delta > 0 else (1 / 1.1)
        self._zoom_step(factor)

    def reset_view(self):
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = -200.0
        self.tkExpose(None)

    def carregar_geometria(self, vertices_np: np.ndarray):
        """Atualiza o VBO diretamente com o array float32 vindo do C."""
        if vertices_np.size == 0:
            self.num_vertices = 0
            self.tkExpose(None)
            return

        dados_contiguos = np.ascontiguousarray(vertices_np, dtype=np.float32)
        self.num_vertices = dados_contiguos.shape[0]

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertice)
        glBufferData(GL_ARRAY_BUFFER, dados_contiguos.nbytes, dados_contiguos, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.tkExpose(None)

    def redraw(self):
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        w = self.winfo_width() or 1
        h = self.winfo_height() or 1
        razao = w / h

        # Projeção ortográfica adaptada com Pan e Zoom
        alcance_y = 600.0 / self.zoom
        alcance_x = alcance_y * razao
        glOrtho(-alcance_x, alcance_x, -alcance_y, alcance_y, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(self.offset_x, self.offset_y, 0.0)

        if self.num_vertices > 0:
            glColor3f(0.8, 0.9, 0.95)
            glLineWidth(1.2)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertice)
            glVertexPointer(2, GL_FLOAT, 0, None)
            glDrawArrays(GL_LINES, 0, self.num_vertices)
            glBindBuffer(GL_ARRAY_BUFFER, 0)


class App:
    def __init__(self, root, models=None):
        self.root = root
        self.root.title("Visualizador Fractal 3D/2D - Acelerado em C")
        self.root.geometry(f"{WIDTH}x{LENGTH}")

        self.models_list = models if models else []
        self.selected_model = None

        try:
            self.motor = MotorLSystem()
            print("[FFI] Motor nativo em C inicializado com sucesso.")
        except Exception as e:
            print(f"[FFI Erro] Não foi possível carregar o motor C: {e}")
            self.motor = None

        self._build_layout()

    def _build_layout(self):
        self._load_menu()
        self._load_configs()
        
        right_container = tk.Frame(self.root, bg=Palette.BACKGROUND_NIGHT)
        right_container.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        
        self._load_footer(right_container)
        self._load_canvas(right_container)

    def _load_menu(self):
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Sair", command=self.root.quit)
        menu_bar.add_cascade(label="Arquivo", menu=file_menu)

        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Resetar Câmera", command=lambda: self.fractal_gl.reset_view())
        menu_bar.add_cascade(label="Visualização", menu=view_menu)
        self.root.config(menu=menu_bar)

    def _load_configs(self):
        painel = tk.Frame(self.root, width=240, bg=Palette.BACKGROUND)
        painel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        painel.pack_propagate(False)

        tk.Label(painel, text="Configurações", font=("Arial", 12, "bold"), bg=Palette.BACKGROUND).pack(pady=15)
        tk.Label(painel, text="Escolha um modelo:", bg=Palette.BACKGROUND).pack(pady=5, anchor='w', padx=10)

        opcoes = [m.name for m in self.models_list]
        self.combo = ttk.Combobox(painel, values=opcoes, state="readonly")
        self.combo.pack(fill=tk.X, padx=10)
        if opcoes:
            self.combo.current(0)

        tk.Button(painel, text="Carregar Modelo", command=self.carregar_modelo_selecionado).pack(fill=tk.X, padx=10, pady=10)

        tk.Frame(painel, height=2, bg="#cccccc").pack(fill=tk.X, padx=10, pady=10)

        tk.Label(painel, text="Ângulo (graus):", bg=Palette.BACKGROUND).pack(anchor="w", padx=10)
        self.slider_ang = tk.Scale(painel, from_=0.0, to=180.0, resolution=0.5, orient=tk.HORIZONTAL)
        self.slider_ang.set(25.7)
        self.slider_ang.pack(fill=tk.X, padx=10, pady=2)

        tk.Label(painel, text="Iterações (n):", bg=Palette.BACKGROUND).pack(anchor="w", padx=10)
        self.slider_iter = tk.Scale(painel, from_=1, to=15, orient=tk.HORIZONTAL)
        self.slider_iter.set(4)
        self.slider_iter.pack(fill=tk.X, padx=10, pady=2)

        tk.Label(painel, text="Tamanho do Segmento:", bg=Palette.BACKGROUND).pack(anchor="w", padx=10)
        self.slider_len = tk.Scale(painel, from_=1, to=50, orient=tk.HORIZONTAL)
        self.slider_len.set(10)
        self.slider_len.pack(fill=tk.X, padx=10, pady=2)

        tk.Button(
            painel, text="Gerar Fractal (GPU)", bg="#4CAF50", fg="white", 
            font=("Arial", 10, "bold"), command=self.processar_fractal
        ).pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=15)

    def _load_footer(self, parent_frame):
        self.footer_frame = tk.Frame(parent_frame, bg=Palette.BACKGROUND, height=30)
        self.footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.footer_frame.pack_propagate(False)

        self.footer_label = tk.Label(
            self.footer_frame, text="Status: Pronto. Nenhum modelo em exibição.", 
            bg=Palette.BACKGROUND, anchor="w", font=("Arial", 9)
        )
        self.footer_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    def _load_canvas(self, parent_frame):
        canvas_frame = tk.Frame(parent_frame, bg=Palette.BACKGROUND_NIGHT)
        canvas_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH)
        self.fractal_gl = FrameFractalGL(canvas_frame)
        self.fractal_gl.pack(fill=tk.BOTH, expand=True)

    def carregar_modelo_selecionado(self):
        nome_escolhido = self.combo.get()
        for model in self.models_list:
            if model.name == nome_escolhido:
                self.selected_model = model
                break

        if self.selected_model:
            # A interface agora atualiza iterações E ângulo automaticamente
            self.slider_iter.set(self.selected_model.iterations)
            self.slider_ang.set(self.selected_model.angle)
            
            self.footer_label.config(text=f"Carregado: {self.selected_model.name} | Axioma: {self.selected_model.axiom}")
            print(f"[UI] Modelo selecionado: {self.selected_model.name}")

    def processar_fractal(self):
        if not self.selected_model or not self.motor:
            print("[Aviso] Selecione um modelo e verifique se a DLL está compilada.")
            return

        n = int(self.slider_iter.get())
        ang = float(self.slider_ang.get())
        comp = float(self.slider_len.get())

        print(f"[Processando] Gerando L-System ({n} iterações em C)...")
        
        palavra_derivada = self.motor.gerar(
            axioma=self.selected_model.axiom,
            regras=self.selected_model.rules,
            iteracoes=n
        )

        vertices = self.motor.gerar_vertices(
            instrucoes=palavra_derivada,
            angulo=ang,
            tamanho_linha=comp
        )

        self.fractal_gl.carregar_geometria(vertices)
        
        info = f"Ativo: {self.selected_model.name} | Segmentos: {len(vertices)//2} | Vértices VRAM: {len(vertices)}"
        self.footer_label.config(text=info)
        print(f"[Render] {info}")