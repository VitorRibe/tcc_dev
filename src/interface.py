import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import threading
from PIL import Image
from OpenGL.GL import *
from pyopengltk import OpenGLFrame
from utils.colors import Palette
from motor_lsystem import MotorLSystem

WIDTH = 1150
LENGTH = 760

class FrameFractalGL(OpenGLFrame):
    def initgl(self):
        r_bg, g_bg, b_bg = Palette.hex_to_rgb_normalized(Palette.BACKGROUND_NIGHT)
        glClearColor(r_bg, g_bg, b_bg, 1.0)
        
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        # Suavização de linhas
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Habilita arrays de vértices e de cores
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        
        self.vbo_vertice = glGenBuffers(1)
        self.vbo_cor = glGenBuffers(1)
        self.num_vertices = 0

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
        self.zoom = max(0.01, min(100.0, self.zoom * factor))
        self.tkExpose(None)

    def _on_zoom(self, event):
        factor = 1.1 if event.delta > 0 else (1 / 1.1)
        self._zoom_step(factor)

    def reset_view(self):
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = -200.0
        self.tkExpose(None)

    def _gerar_cores_gradiente(self, num_vertices: int) -> np.ndarray:
        """Gera um array contíguo (N, 3) interpolando as cores inicial e final."""
        r1, g1, b1 = Palette.hex_to_rgb_normalized(Palette.GRADIENT_START)
        r2, g2, b2 = Palette.hex_to_rgb_normalized(Palette.GRADIENT_END)

        # Vetor de interpolação t de 0.0 a 1.0
        t = np.linspace(0, 1, num_vertices, dtype=np.float32).reshape(-1, 1)

        c1 = np.array([r1, g1, b1], dtype=np.float32)
        c2 = np.array([r2, g2, b2], dtype=np.float32)

        # Cálculo vetorizado: C = C1*(1-t) + C2*t
        cores_np = c1 * (1 - t) + c2 * t
        return np.ascontiguousarray(cores_np)

    def carregar_geometria(self, vertices_np: np.ndarray):
        if vertices_np.size == 0:
            self.num_vertices = 0
            self.tkExpose(None)
            return

        dados_contiguos = np.ascontiguousarray(vertices_np, dtype=np.float32)
        self.num_vertices = dados_contiguos.shape[0]

        # 1. Atualiza o VBO de Vértices
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertice)
        glBufferData(GL_ARRAY_BUFFER, dados_contiguos.nbytes, dados_contiguos, GL_STATIC_DRAW)

        # 2. Gera e atualiza o VBO de Cores (Degradê)
        cores_np = self._gerar_cores_gradiente(self.num_vertices)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_cor)
        glBufferData(GL_ARRAY_BUFFER, cores_np.nbytes, cores_np, GL_STATIC_DRAW)
        
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        
        self.reset_view()
        self.tkExpose(None)

    def exportar_para_imagem(self, filepath: str):
        w = self.winfo_width()
        h = self.winfo_height()
        glReadBuffer(GL_FRONT)
        pixels = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE)
        
        image = Image.frombytes("RGB", (w, h), pixels)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        image.save(filepath)

    def redraw(self):
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        w = self.winfo_width() or 1
        h = self.winfo_height() or 1
        razao = w / h

        alcance_y = 600.0 / self.zoom
        alcance_x = alcance_y * razao
        glOrtho(-alcance_x, alcance_x, -alcance_y, alcance_y, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(self.offset_x, self.offset_y, 0.0)

        if self.num_vertices > 0:
            glLineWidth(1.5)
            
            # Vincula vértices
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertice)
            glVertexPointer(2, GL_FLOAT, 0, None)
            
            # Vincula cores
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_cor)
            glColorPointer(3, GL_FLOAT, 0, None)
            
            glDrawArrays(GL_LINES, 0, self.num_vertices)
            glBindBuffer(GL_ARRAY_BUFFER, 0)


class App:
    def __init__(self, root, models=None):
        self.root = root
        self.root.title("Visualizador Fractal 3D/2D PRO")
        self.root.geometry(f"{WIDTH}x{LENGTH}")
        
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        self.models_list = models if models else []
        self.selected_model = None
        self._is_processing = False

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
        file_menu.add_command(label="Exportar Imagem (PNG)...", command=self._exportar_imagem)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.root.quit)
        menu_bar.add_cascade(label="Arquivo", menu=file_menu)

        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Centralizar Câmera", command=lambda: self.fractal_gl.reset_view())
        menu_bar.add_cascade(label="Visualização", menu=view_menu)
        self.root.config(menu=menu_bar)

    def _load_configs(self):
        painel = tk.Frame(self.root, width=260, bg=Palette.BACKGROUND)
        painel.pack(side=tk.LEFT, fill=tk.Y)
        painel.pack_propagate(False)

        tk.Label(painel, text="L-System Studio", font=("Segoe UI", 14, "bold"), bg=Palette.BACKGROUND, fg="#333").pack(pady=20)
        
        tk.Label(painel, text="Biblioteca de Modelos:", font=("Segoe UI", 9, "bold"), bg=Palette.BACKGROUND, fg="#555").pack(anchor='w', padx=15, pady=(5, 0))
        opcoes = [m.name for m in self.models_list]
        self.combo = ttk.Combobox(painel, values=opcoes, state="readonly", font=("Segoe UI", 9))
        self.combo.pack(fill=tk.X, padx=15, pady=5)
        if opcoes:
            self.combo.current(0)

        ttk.Button(painel, text="Carregar Modelo", command=self.carregar_modelo_selecionado).pack(fill=tk.X, padx=15, pady=5)

        tk.Frame(painel, height=1, bg="#d4d4d4").pack(fill=tk.X, padx=15, pady=15)

        tk.Label(painel, text="Parâmetros de Geração", font=("Segoe UI", 9, "bold"), bg=Palette.BACKGROUND, fg="#555").pack(anchor='w', padx=15, pady=5)

        tk.Label(painel, text="Ângulo de Rotação (graus):", bg=Palette.BACKGROUND, font=("Segoe UI", 9)).pack(anchor="w", padx=15)
        self.slider_ang = ttk.Scale(painel, from_=0.0, to=180.0, orient=tk.HORIZONTAL)
        self.slider_ang.set(90.0)
        self.slider_ang.pack(fill=tk.X, padx=15, pady=2)

        tk.Label(painel, text="Nível de Complexidade (n):", bg=Palette.BACKGROUND, font=("Segoe UI", 9)).pack(anchor="w", padx=15)
        self.slider_iter = ttk.Scale(painel, from_=1, to=15, orient=tk.HORIZONTAL)
        self.slider_iter.set(4)
        self.slider_iter.pack(fill=tk.X, padx=15, pady=2)

        tk.Label(painel, text="Escala do Segmento:", bg=Palette.BACKGROUND, font=("Segoe UI", 9)).pack(anchor="w", padx=15)
        self.slider_len = ttk.Scale(painel, from_=1, to=50, orient=tk.HORIZONTAL)
        self.slider_len.set(10)
        self.slider_len.pack(fill=tk.X, padx=15, pady=2)

        self.btn_gerar = tk.Button(
            painel, text="Renderizar Fractal", bg="#005fb8", fg="white", 
            font=("Segoe UI", 10, "bold"), relief=tk.FLAT, command=self._iniciar_processamento_thread,
            activebackground="#004a90", activeforeground="white", cursor="hand2"
        )
        self.btn_gerar.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=20)

    def _load_footer(self, parent_frame):
        self.footer_frame = tk.Frame(parent_frame, bg="#e0e0e0", height=28)
        self.footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.footer_frame.pack_propagate(False)

        self.footer_label = tk.Label(
            self.footer_frame, text=" Motor de Geração C | Pronto para uso.", 
            bg="#e0e0e0", fg="#444", anchor="w", font=("Segoe UI", 8)
        )
        self.footer_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

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
            self.slider_iter.set(self.selected_model.iterations)
            self.slider_ang.set(self.selected_model.angle)
            self.footer_label.config(text=f" Modelo Ativo: {self.selected_model.name}  |  Axioma Base: {self.selected_model.axiom}")

    def _iniciar_processamento_thread(self):
        if self._is_processing: return
        if not self.selected_model or not self.motor:
            messagebox.showwarning("Aviso", "Selecione um modelo e garanta que o motor C está ativo.")
            return

        self._is_processing = True
        self.btn_gerar.config(state=tk.DISABLED, text="Calculando...", bg="#888")
        self.footer_label.config(text=" Processando matrizes geométricas no backend...")

        n = int(self.slider_iter.get())
        ang = float(self.slider_ang.get())
        comp = float(self.slider_len.get())

        thread = threading.Thread(target=self._processar_fractal_worker, args=(n, ang, comp), daemon=True)
        thread.start()

    def _processar_fractal_worker(self, n: int, ang: float, comp: float):
        try:
            palavra_derivada = self.motor.gerar(self.selected_model.axiom, self.selected_model.rules, n)
            vertices = self.motor.gerar_vertices(palavra_derivada, ang, comp)
            self.root.after(0, self._finalizar_processamento, vertices)
        except Exception as e:
            self.root.after(0, self._falha_processamento, str(e))

    def _finalizar_processamento(self, vertices: np.ndarray):
        self.fractal_gl.carregar_geometria(vertices)
        
        info = f" Renderização Concluída | Segmentos: {len(vertices)//2:,} | Memória VRAM: {len(vertices):,} vértices"
        self.footer_label.config(text=info)
        
        self._is_processing = False
        self.btn_gerar.config(state=tk.NORMAL, text="Renderizar Fractal", bg="#005fb8")

    def _falha_processamento(self, erro: str):
        self.footer_label.config(text=f" Erro de execução nativa: {erro}")
        self._is_processing = False
        self.btn_gerar.config(state=tk.NORMAL, text="Renderizar Fractal", bg="#005fb8")

    def _exportar_imagem(self):
        if self.fractal_gl.num_vertices == 0:
            messagebox.showinfo("Exportar", "Gere um fractal primeiro antes de exportar.")
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("Arquivos PNG", "*.png"), ("Todos os Arquivos", "*.*")],
            title="Exportar Renderização"
        )
        if filepath:
            self.fractal_gl.exportar_para_imagem(filepath)
            self.footer_label.config(text=f" Imagem salva com sucesso em: {filepath}")