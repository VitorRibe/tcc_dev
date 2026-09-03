"""
    Este arquivo define os códigos das cores usadas no sistema
"""
class Palette:
    BACKGROUND = "#eaeaea"
    BACKGROUND_NIGHT = "#1e1e24" 
    
    GRADIENT_START = "#00f2fe"
    GRADIENT_END = "#4facfe"   
    
    LEAF_COLOR = "#2ecc71" # Nova constante de cor padrão para a folhagem

    @classmethod
    def hex_to_rgb_normalized(cls, hex_code: str) -> tuple[float, float, float]:
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) / 255.0 for i in (0, 2, 4))