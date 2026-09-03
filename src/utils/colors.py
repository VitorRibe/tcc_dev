"""
    Este arquivo define os códigos das cores usadas no sistema
"""
class Palette:
    # Cores
    BACKGROUND = "#eaeaea"
    BACKGROUND_NIGHT = "#2c2a2a"

    @classmethod
    # Converte Hex para RGB normalizado (0.0 a 1.0) para uso no OpenGL
    def hex_to_rgb_normalized(cls, hex_code: str) -> tuple[float, float, float]:
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) / 255.0 for i in (0, 2, 4))