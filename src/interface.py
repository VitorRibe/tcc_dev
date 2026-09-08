'''
    Gerencia a interface gráfica e exibição dos fractais
'''
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import numpy as np
import threading
from PIL import Image
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from pyopengltk import OpenGLFrame
from utils.colors import Palette
from motor_lsystem import MotorLSystem
from loader import GrammarModel, save_model

WIDTH = 1200
LENGTH = 800

VERTEX_SHADER = """
#version 120
attribute vec4 position;
attribute vec3 color;
varying vec3 v_color;

uniform mat4 mvp;
uniform float u_time;
uniform float u_wind_strength;

void main() {
    float depth = position.w;
    float swayX = sin(u_time * 2.0 + position.y * 0.1 + position.z * 0.5) * depth * u_wind_strength;
    float swayZ = cos(u_time * 1.5 + position.x * 0.1 + position.y * 0.5) * depth * u_wind_strength;
    
    vec3 pos = position.xyz;
    pos.x += swayX;
    pos.z += swayZ;
    
    gl_Position = mvp * vec4(pos, 1.0);
    v_color = color;
}
"""

FRAGMENT_SHADER = """
#version 120
varying vec3 v_color;
void main() {
    gl_FragColor = vec4(v_color, 1.0);
}
"""

class FrameFractalGL(OpenGLFrame):
    def initgl(self):
        r_bg, g_bg, b_bg = Palette.hex_to_rgb_normalized(Palette.BACKGROUND_NIGHT)
        glClearColor(r_bg, g_bg, b_bg, 1.0)
        
        glDisable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.shader = compileProgram(
            compileShader(VERTEX_SHADER, GL_VERTEX_SHADER),
            compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
        )
        self.pos_loc = glGetAttribLocation(self.shader, "position")
        self.col_loc = glGetAttribLocation(self.shader, "color")
        self.mvp_loc = glGetUniformLocation(self.shader, "mvp")
        self.time_loc = glGetUniformLocation(self.shader, "u_time")
        self.wind_loc = glGetUniformLocation(self.shader, "u_wind_strength")
        
        self.vbo_vertice = glGenBuffers(1)
        self.vbo_cor = glGenBuffers(1)
        self.vbo_folhas_vertice = glGenBuffers(1)
        self.vbo_folhas_cor = glGenBuffers(1)
        
        self.num_vertices = 0
        self.num_folhas_verts = 0
        self.draw_limit = 0
        
        self.is_animating = False
        self.wind_active = False
        self.time_val = 0.0
        self.wind_strength = 0.02
        self.lotes_renderizacao = []

        self.zoom = -800.0
        self.rot_x = 10.0
        self.rot_y = 0.0
        self.pan_x = 0.0
        self.pan_y = -100.0
        
        self.last_x = 0
        self.last_y = 0

        self.bind("<Button-1>", self._on_click)        
        self.bind("<B1-Motion>", self._on_drag_rot)
        self.bind("<Button-3>", self._on_click)        
        self.bind("<B3-Motion>", self._on_drag_pan)
        self.bind("<MouseWheel>", self._on_zoom)

    def _get_perspective(self, fov, aspect, z_near, z_far):
        f = 1.0 / np.tan(np.radians(fov) / 2.0)
        mat = np.zeros((4, 4), dtype=np.float32)
        mat[0, 0] = f / aspect
        mat[1, 1] = f
        mat[2, 2] = (z_far + z_near) / (z_near - z_far)
        mat[2, 3] = -1.0
        mat[3, 2] = (2.0 * z_far * z_near) / (z_near - z_far)
        return mat

    def _get_translation(self, x, y, z):
        mat = np.identity(4, dtype=np.float32)
        mat[0, 3] = x; mat[1, 3] = y; mat[2, 3] = z
        return mat

    def _get_rotation_x(self, angle):
        c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
        mat = np.identity(4, dtype=np.float32)
        mat[1, 1], mat[1, 2] = c, -s
        mat[2, 1], mat[2, 2] = s, c
        return mat

    def _get_rotation_y(self, angle):
        c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
        mat = np.identity(4, dtype=np.float32)
        mat[0, 0], mat[0, 2] = c, s
        mat[2, 0], mat[2, 2] = -s, c
        return mat

    def _on_click(self, event):
        self.last_x, self.last_y = event.x, event.y

    def _on_drag_rot(self, event):
        self.rot_y += (event.x - self.last_x) * 0.5
        self.rot_x += (event.y - self.last_y) * 0.5
        self.last_x, self.last_y = event.x, event.y
        self.tkExpose(None)

    def _on_drag_pan(self, event):
        self.pan_x += (event.x - self.last_x) * abs(self.zoom) * 0.002
        self.pan_y -= (event.y - self.last_y) * abs(self.zoom) * 0.002
        self.last_x, self.last_y = event.x, event.y
        self.tkExpose(None)

    def _on_zoom(self, event):
        self.zoom += 40.0 if event.delta > 0 else -40.0
        if self.zoom > -10.0: self.zoom = -10.0
        self.tkExpose(None)

    def reset_view(self):
        self.zoom, self.rot_x, self.rot_y = -800.0, 10.0, 0.0
        self.pan_x, self.pan_y = 0.0, -100.0
        self.tkExpose(None)

    def carregar_geometria(self, vertices_np: np.ndarray, folhas_np: np.ndarray):
        self.is_animating = False
        
        if vertices_np.size > 0:
            segmentos = vertices_np.reshape(-1, 2, 4)
            prof_max = np.max(segmentos[:, 0, 3]) if len(segmentos) > 0 else 1
            prof_max = prof_max if prof_max > 0 else 1

            ordem = np.argsort(segmentos[:, 0, 3])
            segmentos_ordenados = segmentos[ordem]
            vertices_ordenados = segmentos_ordenados.reshape(-1, 4)
            
            self.num_vertices = vertices_ordenados.shape[0]
            self.draw_limit = self.num_vertices

            geom_xyzw = np.ascontiguousarray(vertices_ordenados, dtype=np.float32)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertice)
            glBufferData(GL_ARRAY_BUFFER, geom_xyzw.nbytes, geom_xyzw, GL_STATIC_DRAW)

            self.lotes_renderizacao = []
            start = 0
            unique_depths, counts = np.unique(segmentos_ordenados[:, 0, 3], return_counts=True)
            for depth, count in zip(unique_depths, counts):
                num_verts = count * 2
                width = max(1.0, 5.0 - (depth * 0.4)) 
                self.lotes_renderizacao.append((start, num_verts, width))
                start += num_verts

            self._atualizar_cores_vbo(vertices_ordenados[:, 3], prof_max)
        else:
            self.num_vertices = 0
            self.draw_limit = 0

        if folhas_np.size > 0:
            folhas_xyzw = np.ascontiguousarray(folhas_np, dtype=np.float32)
            self.num_folhas_verts = folhas_xyzw.shape[0]
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_folhas_vertice)
            glBufferData(GL_ARRAY_BUFFER, folhas_xyzw.nbytes, folhas_xyzw, GL_STATIC_DRAW)
            self._atualizar_cores_folhas()
        else:
            self.num_folhas_verts = 0

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.reset_view()

    def _atualizar_cores_vbo(self, profundidades: np.ndarray, prof_max: float):
        r1, g1, b1 = Palette.hex_to_rgb_normalized(Palette.GRADIENT_START)
        r2, g2, b2 = Palette.hex_to_rgb_normalized(Palette.GRADIENT_END)
        c1, c2 = np.array([r1, g1, b1], dtype=np.float32), np.array([r2, g2, b2], dtype=np.float32)
        
        t = (profundidades / prof_max).reshape(-1, 1)
        cores_np = np.ascontiguousarray(c1 * (1 - t) + c2 * t, dtype=np.float32)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_cor)
        glBufferData(GL_ARRAY_BUFFER, cores_np.nbytes, cores_np, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def _atualizar_cores_folhas(self):
        """Aplica textura volumétrica nas folhas calculando multiplicadores."""
        if self.num_folhas_verts == 0: return
        r, g, b = Palette.hex_to_rgb_normalized(Palette.LEAF_COLOR)
        
        base_c = np.clip([r*0.4, g*0.4, b*0.4], 0, 1)
        mid_c  = np.clip([r*0.8, g*0.8, b*0.8], 0, 1)
        tip_c  = np.clip([r*1.2, g*1.2, b*1.2], 0, 1)
        
        # Padrão V-Fold (Triângulo Esquerdo, Triângulo Direito)
        pattern = np.array([base_c, mid_c, tip_c, base_c, tip_c, mid_c], dtype=np.float32)
        num_leaves = self.num_folhas_verts // 6
        
        cores_folhas = np.tile(pattern, (num_leaves, 1))
        cores_folhas = np.ascontiguousarray(cores_folhas, dtype=np.float32)
        
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_folhas_cor)
        glBufferData(GL_ARRAY_BUFFER, cores_folhas.nbytes, cores_folhas, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.tkExpose(None)

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
        if self.is_animating: self.after(16, self._anim_loop)

    def toggle_wind(self, active: bool, strength: float):
        self.wind_active, self.wind_strength = active, strength
        if self.wind_active: self._wind_loop()
        else: self.tkExpose(None)

    def _wind_loop(self):
        if not self.wind_active: return
        self.time_val += 0.05
        self.tkExpose(None)
        self.after(16, self._wind_loop)

    def exportar_para_imagem(self, filepath: str):
        w, h = self.winfo_width(), self.winfo_height()
        glReadBuffer(GL_FRONT)
        pixels = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE)
        Image.frombytes("RGB", (w, h), pixels).transpose(Image.FLIP_TOP_BOTTOM).save(filepath)

    def redraw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        aspect = (self.winfo_width() or 1) / (self.winfo_height() or 1)
        
        proj = self._get_perspective(45.0, aspect, 1.0, 10000.0)
        view = self._get_translation(self.pan_x, self.pan_y, self.zoom)
        rot_x, rot_y = self._get_rotation_x(self.rot_x), self._get_rotation_y(self.rot_y)
        
        mvp = np.dot(proj, np.dot(view, np.dot(rot_x, rot_y)))
        mvp_col_major = np.ascontiguousarray(mvp.T, dtype=np.float32)

        glUseProgram(self.shader)
        glUniformMatrix4fv(self.mvp_loc, 1, GL_FALSE, mvp_col_major)
        glUniform1f(self.time_loc, self.time_val)
        glUniform1f(self.wind_loc, self.wind_strength if self.wind_active else 0.0)

        # 1. Renderizar Troncos (Linhas)
        if self.draw_limit > 0:
            glEnableVertexAttribArray(self.pos_loc)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertice)
            glVertexAttribPointer(self.pos_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

            glEnableVertexAttribArray(self.col_loc)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_cor)
            glVertexAttribPointer(self.col_loc, 3, GL_FLOAT, GL_FALSE, 0, None)
            
            desenhado = 0
            for start, num_verts, width in self.lotes_renderizacao:
                if desenhado >= self.draw_limit: break
                verts_a_desenhar = min(num_verts, self.draw_limit - desenhado)
                glLineWidth(width)
                glDrawArrays(GL_LINES, start, verts_a_desenhar)
                desenhado += verts_a_desenhar
                
            glDisableVertexAttribArray(self.pos_loc)
            glDisableVertexAttribArray(self.col_loc)

        # 2. Renderizar Folhagem (Triângulos Volumétricos)
        if self.num_folhas_verts > 0 and self.draw_limit >= self.num_vertices:
            glEnableVertexAttribArray(self.pos_loc)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_folhas_vertice)
            glVertexAttribPointer(self.pos_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

            glEnableVertexAttribArray(self.col_loc)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_folhas_cor)
            glVertexAttribPointer(self.col_loc, 3, GL_FLOAT, GL_FALSE, 0, None)
            
            glDisable(GL_CULL_FACE)
            glDrawArrays(GL_TRIANGLES, 0, self.num_folhas_verts)
            
            glDisableVertexAttribArray(self.pos_loc)
            glDisableVertexAttribArray(self.col_loc)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glUseProgram(0)


class App:
    def __init__(self, root, models=None):
        self.root = root
        self.root.title("L-System Studio 3D PRO - Folhagem Orgânica & Física")
        self.root.geometry(f"{WIDTH}x{LENGTH}")
        
        style = ttk.Style()
        if 'clam' in style.theme_names(): style.theme_use('clam')

        self.models_list = models if models else []
        self.selected_model = None
        self._is_processing = False
        self.vertices_raw = None

        self.var_wind = tk.BooleanVar(value=False)
        self.var_wind_strength = tk.DoubleVar(value=0.04)

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
        file_menu.add_command(label="Exportar Malha 3D (.OBJ)...", command=self._exportar_obj)
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
        self.btn_gerar = tk.Button(tab_gerar, text="Renderizar Fractal Instanciado", bg="#005fb8", fg="white", font=("Segoe UI", 10, "bold"), command=self._iniciar_processamento_thread)
        self.btn_gerar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=15)

        tab_visual = tk.Frame(notebook, bg=Palette.BACKGROUND)
        notebook.add(tab_visual, text="Visual")
        tk.Label(tab_visual, text="Física de Vento (GPU):", font=("Segoe UI", 9, "bold"), bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=5)
        ttk.Checkbutton(tab_visual, text="Habilitar Simulação", variable=self.var_wind, command=self._atualizar_vento).pack(anchor='w', padx=5)
        tk.Label(tab_visual, text="Força do Vento:", bg=Palette.BACKGROUND).pack(anchor='w', padx=5)
        self.slider_wind = ttk.Scale(tab_visual, from_=0.0, to=0.2, orient=tk.HORIZONTAL, variable=self.var_wind_strength, command=lambda e: self._atualizar_vento())
        self.slider_wind.pack(fill=tk.X, padx=5)
        
        ttk.Separator(tab_visual, orient='horizontal').pack(fill=tk.X, padx=5, pady=10)
        tk.Label(tab_visual, text="Personalizar Tronco:", font=("Segoe UI", 9, "bold"), bg=Palette.BACKGROUND).pack(anchor='w', padx=5)
        ttk.Button(tab_visual, text="Cor Inicial", command=lambda: self._escolher_cor("start")).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(tab_visual, text="Cor Final", command=lambda: self._escolher_cor("end")).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(tab_visual, text="Personalizar Folhagem:", font=("Segoe UI", 9, "bold"), bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=(10,0))
        ttk.Button(tab_visual, text="Cor das Folhas", command=lambda: self._escolher_cor("leaf")).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Separator(tab_visual, orient='horizontal').pack(fill=tk.X, padx=5, pady=10)
        tk.Label(tab_visual, text="Renderização Progressiva:", font=("Segoe UI", 9, "bold"), bg=Palette.BACKGROUND).pack(anchor='w', padx=5)
        self.slider_anim = ttk.Scale(tab_visual, from_=0.1, to=10.0, orient=tk.HORIZONTAL)
        self.slider_anim.set(1.0)
        self.slider_anim.pack(fill=tk.X, padx=5)
        ttk.Button(tab_visual, text="▶ Play Animação", command=lambda: self.fractal_gl.play_animation(self.slider_anim.get())).pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(tab_visual, text="⏹ Parar / Mostrar Tudo", command=self._parar_animacao).pack(fill=tk.X, padx=5)
        ttk.Button(tab_visual, text="Resetar Câmera Orbital", command=lambda: self.fractal_gl.reset_view()).pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=15)

        tab_sandbox = tk.Frame(notebook, bg=Palette.BACKGROUND)
        notebook.add(tab_sandbox, text="Sandbox")
        tk.Label(tab_sandbox, text="Nome:", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=2)
        self.sb_nome = ttk.Entry(tab_sandbox)
        self.sb_nome.pack(fill=tk.X, padx=5)
        tk.Label(tab_sandbox, text="Axioma Base:", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=(5,2))
        self.sb_axioma = ttk.Entry(tab_sandbox)
        self.sb_axioma.pack(fill=tk.X, padx=5)
        tk.Label(tab_sandbox, text="Ângulo (graus):", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=(5,2))
        self.sb_angulo = ttk.Entry(tab_sandbox)
        self.sb_angulo.insert(0, "90.0")
        self.sb_angulo.pack(fill=tk.X, padx=5)
        tk.Label(tab_sandbox, text="Iterações:", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=(5,2))
        self.sb_iter = ttk.Entry(tab_sandbox)
        self.sb_iter.insert(0, "4")
        self.sb_iter.pack(fill=tk.X, padx=5)
        tk.Label(tab_sandbox, text="Regras 3D (Com Folha '@'):", bg=Palette.BACKGROUND).pack(anchor='w', padx=5, pady=(5,2))
        self.sb_regras = tk.Text(tab_sandbox, height=5, font=("Consolas", 9))
        self.sb_regras.pack(fill=tk.X, padx=5)
        ttk.Button(tab_sandbox, text="Salvar Novo Fractal", command=self._salvar_sandbox).pack(fill=tk.X, padx=5, pady=10)

    def _atualizar_vento(self):
        self.fractal_gl.toggle_wind(self.var_wind.get(), self.var_wind_strength.get())

    def _escolher_cor(self, tipo: str):
        cor_hex = colorchooser.askcolor(title="Escolha a Cor")[1]
        if cor_hex:
            if tipo == "start": Palette.GRADIENT_START = cor_hex
            elif tipo == "end": Palette.GRADIENT_END = cor_hex
            elif tipo == "leaf": Palette.LEAF_COLOR = cor_hex
            
            if self.vertices_raw is not None:
                if tipo in ["start", "end"]:
                    self.fractal_gl.carregar_geometria(self.vertices_raw, np.array([]))
                elif tipo == "leaf":
                    self.fractal_gl._atualizar_cores_folhas()

    def _parar_animacao(self):
        self.fractal_gl.is_animating = False
        self.fractal_gl.draw_limit = self.fractal_gl.num_vertices
        self.fractal_gl.tkExpose(None)

    def _salvar_sandbox(self):
        nome, axioma = self.sb_nome.get().strip(), self.sb_axioma.get().strip()
        regras_raw = self.sb_regras.get("1.0", tk.END).strip()
        if not nome or not axioma or not regras_raw:
            messagebox.showerror("Erro", "Preencha Nome, Axioma e Regras.")
            return

        try:
            angulo, iteracoes = float(self.sb_angulo.get().strip()), int(self.sb_iter.get().strip())
        except ValueError:
            messagebox.showerror("Erro", "Campos numéricos inválidos.")
            return

        regras_dict = {}
        try:
            for p in regras_raw.replace("\n", "").split(";"):
                if "=" in p:
                    k, v = p.split("=")
                    regras_dict[k.strip()] = v.strip()
        except:
            messagebox.showerror("Erro", "Formato inválido. Use A=B;C=D")
            return

        novo_modelo = GrammarModel(nome, axioma, iteracoes, angulo, regras_dict)
        save_model("models.json", novo_modelo)
        
        self.models_list.append(novo_modelo)
        self.combo['values'] = [m.name for m in self.models_list]
        self.combo.set(nome)
        self.carregar_modelo_selecionado()
        messagebox.showinfo("Sucesso", "Modelo salvo e carregado!")

    def _load_footer(self, parent_frame):
        self.footer_frame = tk.Frame(parent_frame, bg="#e0e0e0", height=28)
        self.footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.footer_frame.pack_propagate(False)

        self.footer_label = tk.Label(self.footer_frame, text=" L-System Studio Folhagem | Pronto.", bg="#e0e0e0", fg="#444", anchor="w", font=("Segoe UI", 8))
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
        if self._is_processing or not self.selected_model: return
        self._is_processing = True
        self.btn_gerar.config(state=tk.DISABLED, text="Calculando Instâncias 3D...")
        
        n = min(15, int(self.slider_iter.get()))
        threading.Thread(target=self._processar_fractal_worker, args=(n, float(self.slider_ang.get()), float(self.slider_len.get())), daemon=True).start()

    def _processar_fractal_worker(self, n: int, ang: float, comp: float):
        try:
            palavra = self.motor.gerar(self.selected_model.axiom, self.selected_model.rules, n)
            vertices = self.motor.gerar_vertices(palavra, ang, comp)
            folhas = self.motor.gerar_folhas(palavra, ang, comp)
            self.root.after(0, self._finalizar_processamento, vertices, folhas)
        except Exception as e:
            self.root.after(0, lambda: self.footer_label.config(text=f" Erro: {e}"))
            self._is_processing = False
            self.btn_gerar.config(state=tk.NORMAL, text="Renderizar Fractal Instanciado")

    def _finalizar_processamento(self, vertices: np.ndarray, folhas: np.ndarray):
        self.vertices_raw = vertices
        self.fractal_gl.carregar_geometria(vertices, folhas)
        self.footer_label.config(text=f" Concluído | {len(vertices)//2:,} arestas | {len(folhas)//6:,} folhas texturizadas.")
        self._is_processing = False
        self.btn_gerar.config(state=tk.NORMAL, text="Renderizar Fractal Instanciado")
        
        if self.var_wind.get():
            self._atualizar_vento()

    def _exportar_imagem(self):
        if self.fractal_gl.num_vertices == 0: return
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if filepath:
            self.fractal_gl.exportar_para_imagem(filepath)
            self.footer_label.config(text=f" Imagem exportada: {filepath}")

    def _exportar_obj(self):
        if self.vertices_raw is None or len(self.vertices_raw) == 0:
            messagebox.showinfo("Exportar", "Gere um modelo 3D primeiro.")
            return
            
        filepath = filedialog.asksaveasfilename(defaultextension=".obj", filetypes=[("Wavefront OBJ", "*.obj")], title="Exportar Modelo 3D")
        if not filepath: return

        try:
            with open(filepath, 'w') as f:
                f.write("# Gerado nativamente via L-System Studio 3D PRO\n")
                f.write(f"o {self.selected_model.name.replace(' ', '_')}\n")
                
                for i in range(len(self.vertices_raw)):
                    f.write(f"v {self.vertices_raw[i, 0]} {self.vertices_raw[i, 1]} {self.vertices_raw[i, 2]}\n")
                    
                for i in range(1, len(self.vertices_raw), 2):
                    f.write(f"l {i} {i+1}\n")
                    
            self.footer_label.config(text=f" Malha 3D (.OBJ) compilada em: {filepath}")
            messagebox.showinfo("Sucesso", "Modelo Wavefront .OBJ gerado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro de I/O", str(e))