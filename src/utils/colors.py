"""
    Este arquivo define os códigos das cores usadas no sistema
"""
class Palette:
    BACKGROUND = "#eaeaea"
    BACKGROUND_NIGHT = "#1e1e24" # Um pouco mais escuro para destacar o neon
    
    # Cores do degradê (Exemplo: Cyberpunk / Neon Vibe)
    GRADIENT_START = "#00f2fe" # Ciano brilhante
    GRADIENT_END = "#4facfe"   # Azul profundo
    
    # Alternativa (Fogo/Magma): 
    # GRADIENT_START = "#f12711"
    # GRADIENT_END = "#f5af19"

    @classmethod
    def hex_to_rgb_normalized(cls, hex_code: str) -> tuple[float, float, float]:
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) / 255.0 for i in (0, 2, 4))