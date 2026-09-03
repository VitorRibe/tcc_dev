import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import numpy as np
import threading
from PIL import Image
from OpenGL.GL import *
from pyopengltk import OpenGLFrame
from utils.colors import Palette
from motor_lsystem import MotorLSystem
from loader import GrammarModel, save_model

WIDTH = 1200
LENGTH = 800

class FrameFractalGL(OpenGLFrame):
    def initgl(self):
        r_bg, g_bg, b_bg = Palette.hex_to_rgb_normalized(Palette.BACKGROUND_NIGHT)
        glClearColor(r_bg, g_bg, b_bg, 1.0)
        
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        
        self.vbo_vertice = glGenBuffers(1)
        self.vbo_cor = glGenBuffers(1)
        
        self.num_vertices = 0
        self.draw_limit = 0
        self.is_animating = False

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
        r1, g1, b1 = Palette.hex_to_rgb_normalized(Palette.GRADIENT_START)
        r2, g2, b2 = Palette.hex_to_rgb_normalized(Palette.GRADIENT_END)
        t = np.linspace(0, 1, num_vertices, dtype=np.float32).reshape(-1, 1)
        c1 = np.array([r1, g1, b1], dtype=np.float32)
        c2 = np.array([r2, g2, b2], dtype=np.float32)
        cores_np = c1 * (1 - t) + c2 * t
        return np.ascontiguousarray(cores_np)

    def atualizar_cores_vbo(self):
        if self.num_vertices == 0: return
        cores_np = self._gerar_cores_gradiente(self.num_vertices)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_cor)
        glBufferData(GL_ARRAY_BUFFER, cores_np.nbytes, cores_np, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.tkExpose(None)

    def carregar_geometria(self, vertices_np: np.ndarray):
        self.is_animating = False
        if vertices_np.size == 0:
            self.num_vertices = 0
            self.draw_limit = 0
            self.tkExpose(None)
            return

        dados_contiguos = np.ascontiguousarray(vertices_np, dtype=np.float32)
        self.num_vertices = dados_contiguos.shape[0]
        self.draw_limit = self.num_vertices

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertice)
        glBufferData(GL_ARRAY_BUFFER, dados_contiguos.nbytes, dados_contiguos, GL_STATIC_DRAW)
        
        self.atualizar_cores_vbo()
        self.reset_view()

    def play_animation(self, speed_multiplier: float):
        if self.num_vertices == 0: return
        self.is_animating = True
        self.draw_limit = 0
        self.step_size = max(2, int((self.num_vertices * speed_multiplier) / 100))
        self._anim_loop()

    def _anim_loop(self):
        if not self.is_animating: return
        self.draw_limit += self.step_size
        if self.draw_limit >= self.num_vertices:
            self.draw_limit = self.num_vertices
            self.is_animating = False
        
        self.tkExpose(None)
        if self.is_animating:
            self.after(16, self._anim_loop)

    def exportar_para_imagem(self, filepath: str):
        w, h = self.winfo_width(), self.winfo_height()
        glReadBuffer(GL_FRONT)
        pixels = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE)
        image = Image.frombytes("RGB", (w, h), pixels).transpose(Image.FLIP_TOP_BOTTOM)
        image.save(filepath)

    def redraw(self):
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        w, h = self.winfo_width() or 1, self.winfo_height() or 1
        razao = w / h
        alcance_y = 600.0 / self.zoom
        alcance_x = alcance_y * razao
        glOrtho(-alcance_x, alcance_x, -alcance_y, alcance_y, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(self.offset_x, self.offset_y, 0.0)

        if self.draw_limit > 0:
            glLineWidth(1.5)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertice)
            glVertexPointer(2, GL_FLOAT, 0, None)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_cor)
            glColorPointer(3, GL_FLOAT, 0, None)
            glDrawArrays(GL_LINES, 0, self.draw_limit)
            glBindBuffer(GL_ARRAY_BUFFER, 0)


class App:
    def __init__(self, root, models=None):
        self.root = root
        self.root.title("Visualizador Fractal 3D/2D PRO - L-System Studio")
        self.root.geometry(f"{WIDTH}x{LENGTH}")
        
        style = ttk.Style()
        if 'clam' in style.theme_names(): style.theme_use('clam')

        self.models_list = models if models else []
        self.selected_model = None
        self._is_processing = False

        try:
            self.motor = MotorLSystem()
        except Exception as e:
            print(f"[FFI Erro] {e}")
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
        file_menu.add_command(label="Exportar Imagem (PNG)...", command=lambda: self._exportar_imagem())
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.root.quit)
        menu_bar.add_cascade(label="Arquivo", menu=file_menu)
        self.root.config(menu=menu_bar)

    def _load_configs(self):
        painel = tk.Frame(self.root, width=320, bg=Palette.BACKGROUND)
        painel.pack(side=tk.LEFT, fill=tk.Y)
        painel.pack_propagate(False)

        tk.Label(painel, text="L-System Studio", font=("Segoe UI", 16, "bold"), bg=Palette.BACKGROUND).pack(pady=15)
        
        notebook = ttk.Notebook(painel)
        notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        # ABA 1: PARÂMETROS BÁSICOS
        tab_gerar = tk.Frame(notebook, bg=Palette.BACKGROUND)
        notebook.add(tab_gerar, text="Geração")

        tk.Label(tab_gerar, text="Biblioteca:", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=5)
        self.combo = ttk.Combobox(tab_gerar, values=[m.name for m in self.models_list], state="readonly")
        self.combo.pack(fill=tk.X, padx=5)
        if self.models_list: self.combo.current(0)
        ttk.Button(tab_gerar, text="Carregar Modelo", command=self.carregar_modelo_selecionado).pack(fill=tk.X, padx=5, pady=5)

        ttk.Separator(tab_gerar, orient='horizontal').pack(fill=tk.X, padx=5, pady=10)

        tk.Label(tab_gerar, text="Ângulo (graus):", bg=Palette.BACKGROUND).pack(anchor="w", padx=5)
        self.slider_ang = ttk.Scale(tab_gerar, from_=0.0, to=180.0, orient=tk.HORIZONTAL)
        self.slider_ang.pack(fill=tk.X, padx=5)

        tk.Label(tab_gerar, text="Iterações (Máx 15):", bg=Palette.BACKGROUND).pack(anchor="w", padx=5, pady=(10,0))
        self.slider_iter = ttk.Scale(tab_gerar, from_=1, to=15, orient=tk.HORIZONTAL)
        self.slider_iter.pack(fill=tk.X, padx=5)

        tk.Label(tab_gerar, text="Escala do Segmento:", bg=Palette.BACKGROUND).pack(anchor="w", padx=5, pady=(10,0))
        self.slider_len = ttk.Scale(tab_gerar, from_=1, to=50, orient=tk.HORIZONTAL)
        self.slider_len.pack(fill=tk.X, padx=5)

        self.btn_gerar = tk.Button(tab_gerar, text="Renderizar Fractal (C)", bg="#005fb8", fg="white", font=("Segoe UI", 10, "bold"), command=self._iniciar_processamento_thread)
        self.btn_gerar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=15)

        # ABA 2: VISUAL & ANIMAÇÃO
        tab_visual = tk.Frame(notebook, bg=Palette.BACKGROUND)
        notebook.add(tab_visual, text="Visual")

        tk.Label(tab_visual, text="Personalizar Cores:", font=("Segoe UI", 9, "bold"), bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=5)
        ttk.Button(tab_visual, text="Cor Inicial", command=lambda: self._escolher_cor(True)).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(tab_visual, text="Cor Final", command=lambda: self._escolher_cor(False)).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Separator(tab_visual, orient='horizontal').pack(fill=tk.X, padx=5, pady=10)
        
        tk.Label(tab_visual, text="Renderização Progressiva:", font=("Segoe UI", 9, "bold"), bg=Palette.BACKGROUND).pack(anchor='w', padx=5)
        tk.Label(tab_visual, text="Velocidade:", bg=Palette.BACKGROUND).pack(anchor='w', padx=5)
        self.slider_anim = ttk.Scale(tab_visual, from_=0.1, to=10.0, orient=tk.HORIZONTAL)
        self.slider_anim.set(1.0)
        self.slider_anim.pack(fill=tk.X, padx=5)
        ttk.Button(tab_visual, text="▶ Play Animação", command=lambda: self.fractal_gl.play_animation(self.slider_anim.get())).pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(tab_visual, text="⏹ Parar / Mostrar Tudo", command=self._parar_animacao).pack(fill=tk.X, padx=5)

        ttk.Separator(tab_visual, orient='horizontal').pack(fill=tk.X, padx=5, pady=10)
        ttk.Button(tab_visual, text="Resetar Câmera", command=lambda: self.fractal_gl.reset_view()).pack(fill=tk.X, padx=5)

        # ABA 3: SANDBOX
        tab_sandbox = tk.Frame(notebook, bg=Palette.BACKGROUND)
        notebook.add(tab_sandbox, text="Sandbox")

        tk.Label(tab_sandbox, text="Nome:", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=2)
        self.sb_nome = ttk.Entry(tab_sandbox)
        self.sb_nome.pack(fill=tk.X, padx=5)

        tk.Label(tab_sandbox, text="Axioma Base:", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=(5,2))
        self.sb_axioma = ttk.Entry(tab_sandbox)
        self.sb_axioma.pack(fill=tk.X, padx=5)

        # Novos campos numéricos adicionados na Sandbox
        tk.Label(tab_sandbox, text="Ângulo (graus):", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=(5,2))
        self.sb_angulo = ttk.Entry(tab_sandbox)
        self.sb_angulo.insert(0, "90.0")
        self.sb_angulo.pack(fill=tk.X, padx=5)

        tk.Label(tab_sandbox, text="Iterações Recomendadas:", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=(5,2))
        self.sb_iter = ttk.Entry(tab_sandbox)
        self.sb_iter.insert(0, "4")
        self.sb_iter.pack(fill=tk.X, padx=5)

        tk.Label(tab_sandbox, text="Regras (Ex: F=0.5:FF,0.5:F[+F]):", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=(5,2))
        self.sb_regras = tk.Text(tab_sandbox, height=5, font=("Consolas", 9))
        self.sb_regras.pack(fill=tk.X, padx=5)

        ttk.Button(tab_sandbox, text="Salvar Novo Fractal", command=self._salvar_sandbox).pack(fill=tk.X, padx=5, pady=10)


    def _escolher_cor(self, is_start: bool):
        cor_hex = colorchooser.askcolor(title="Escolha a Cor")[1]
        if cor_hex:
            if is_start: Palette.GRADIENT_START = cor_hex
            else: Palette.GRADIENT_END = cor_hex
            self.fractal_gl.atualizar_cores_vbo()

    def _parar_animacao(self):
        self.fractal_gl.is_animating = False
        self.fractal_gl.draw_limit = self.fractal_gl.num_vertices
        self.fractal_gl.tkExpose(None)

    def _salvar_sandbox(self):
        nome = self.sb_nome.get().strip()
        axioma = self.sb_axioma.get().strip()
        regras_raw = self.sb_regras.get("1.0", tk.END).strip()

        if not nome or not axioma or not regras_raw:
            messagebox.showerror("Erro", "Preencha Nome, Axioma e Regras.")
            return

        try:
            angulo = float(self.sb_angulo.get().strip())
        except ValueError:
            messagebox.showerror("Erro", "O campo Ângulo deve ser um número válido (ex: 90.0).")
            return

        try:
            iteracoes = int(self.sb_iter.get().strip())
        except ValueError:
            messagebox.showerror("Erro", "O campo Iterações deve ser um número inteiro (ex: 4).")
            return

        regras_dict = {}
        try:
            pares = regras_raw.replace("\n", "").split(";")
            for p in pares:
                if "=" in p:
                    k, v = p.split("=")
                    regras_dict[k.strip()] = v.strip()
        except:
            messagebox.showerror("Erro", "Formato de regra inválido. Use A=B;C=D")
            return

        novo_modelo = GrammarModel(nome, axioma, iteracoes, angulo, regras_dict)
        save_model("models.json", novo_modelo)
        
        self.models_list.append(novo_modelo)
        self.combo['values'] = [m.name for m in self.models_list]
        self.combo.set(nome)
        self.carregar_modelo_selecionado()
        messagebox.showinfo("Sucesso", "Modelo salvo em models.json e carregado na aba de Geração!")

    def _load_footer(self, parent_frame):
        self.footer_frame = tk.Frame(parent_frame, bg="#e0e0e0", height=28)
        self.footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.footer_frame.pack_propagate(False)

        self.footer_label = tk.Label(
            self.footer_frame, text=" L-System Studio | Pronto.", 
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
            self.slider_len.set(10)
            self.footer_label.config(text=f" Modelo Ativo: {self.selected_model.name}")

    def _iniciar_processamento_thread(self):
        if self._is_processing: return
        if not self.selected_model: return

        self._is_processing = True
        self.btn_gerar.config(state=tk.DISABLED, text="Calculando...")
        
        n = int(self.slider_iter.get())
        ang = float(self.slider_ang.get())
        comp = float(self.slider_len.get())
        
        if n > 15: n = 15 

        threading.Thread(target=self._processar_fractal_worker, args=(n, ang, comp), daemon=True).start()

    def _processar_fractal_worker(self, n: int, ang: float, comp: float):
        try:
            palavra = self.motor.gerar(self.selected_model.axiom, self.selected_model.rules, n)
            vertices = self.motor.gerar_vertices(palavra, ang, comp)
            self.root.after(0, self._finalizar_processamento, vertices)
        except Exception as e:
            self.root.after(0, lambda: self.footer_label.config(text=f" Erro: {e}"))
            self._is_processing = False
            self.btn_gerar.config(state=tk.NORMAL, text="Renderizar Fractal (C)")

    def _finalizar_processamento(self, vertices: np.ndarray):
        self.fractal_gl.carregar_geometria(vertices)
        self.footer_label.config(text=f" Concluído | {len(vertices)//2:,} segmentos de linha computados.")
        self._is_processing = False
        self.btn_gerar.config(state=tk.NORMAL, text="Renderizar Fractal (C)")

    def _exportar_imagem(self):
        if self.fractal_gl.num_vertices == 0: return
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if filepath:
            self.fractal_gl.exportar_para_imagem(filepath)
            self.footer_label.config(text=f" Imagem exportada: {filepath}")