"""
    colors.py
    Este arquivo define os códigos das cores usadas no sistema
"""
class Palette:
    BACKGROUND = "#eaeaea"
    BACKGROUND_NIGHT = "#2c2a2a"
    FRACTAL_LINE = "#cce6f2" # Nova cor centralizada para os vértices do L-System

    @classmethod
    def hex_to_rgb_normalized(cls, hex_code: str) -> tuple[float, float, float]:
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) / 255.0 for i in (0, 2, 4))