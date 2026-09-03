import ctypes
import os
import platform
import numpy as np

class MotorLSystem:
    """Interface FFI para o motor de substituição e cálculo geométrico em C."""
    
    def __init__(self, caminho_dll: str = None):
        if caminho_dll is None:
            ext = '.dll' if platform.system() == 'Windows' else '.so'
            caminho_dll = f'motor_lsystem{ext}'
            
        caminho_absoluto = os.path.join(os.path.dirname(os.path.abspath(__file__)), caminho_dll)
        if not os.path.exists(caminho_absoluto):
            raise FileNotFoundError(f"Biblioteca compilada não encontrada em: {caminho_absoluto}")
            
        self.lib = ctypes.CDLL(caminho_absoluto)

        # expandir_lsystem_c
        self.lib.expandir_lsystem_c.argtypes = [
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int
        ]
        self.lib.expandir_lsystem_c.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.liberar_memoria_c.argtypes = [ctypes.POINTER(ctypes.c_char)]
        self.lib.liberar_memoria_c.restype = None

        # calcular_vertices_c
        self.lib.calcular_vertices_c.argtypes = [
            ctypes.c_char_p,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.POINTER(ctypes.c_int)
        ]
        self.lib.calcular_vertices_c.restype = ctypes.POINTER(ctypes.c_float)
        self.lib.liberar_vertices_c.argtypes = [ctypes.POINTER(ctypes.c_float)]
        self.lib.liberar_vertices_c.restype = None

    def gerar(self, axioma: str, regras: dict, iteracoes: int) -> str:
        axioma_bytes = axioma.encode('utf-8')
        
        ArrayRegras = ctypes.c_char_p * 256
        regras_c = ArrayRegras()
        for i in range(256):
            regras_c[i] = None
            
        for k, v in regras.items():
            regras_c[ord(k)] = v.encode('utf-8')

        ponteiro_resultado = self.lib.expandir_lsystem_c(axioma_bytes, regras_c, iteracoes)
        if not ponteiro_resultado:
            raise MemoryError("Falha de alocação no motor nativo (C).")

        resultado_bytes = ctypes.cast(ponteiro_resultado, ctypes.c_char_p).value
        resultado_str = resultado_bytes.decode('utf-8')
        self.lib.liberar_memoria_c(ponteiro_resultado)

        return resultado_str

    def gerar_vertices(self, instrucoes: str, angulo: float, tamanho_linha: float) -> np.ndarray:
        instrucoes_bytes = instrucoes.encode('utf-8')
        num_vertices = ctypes.c_int(0)

        ponteiro_pts = self.lib.calcular_vertices_c(
            instrucoes_bytes, 
            float(angulo), 
            float(tamanho_linha), 
            ctypes.byref(num_vertices)
        )

        if not ponteiro_pts or num_vertices.value == 0:
            return np.array([], dtype=np.float32)

        tamanho_array = num_vertices.value * 2
        array_c = ctypes.cast(ponteiro_pts, ctypes.POINTER(ctypes.c_float * tamanho_array))
        
        vertices_np = np.frombuffer(array_c.contents, dtype=np.float32).copy()
        self.lib.liberar_vertices_c(ponteiro_pts)

        return vertices_np.reshape((-1, 2))