import numpy as np
from vispy import app, scene

def desenhar_lsystem_com_vertices(vertices_np: np.ndarray):
    if vertices_np.size == 0:
        print("Nenhum vértice para renderizar.")
        return

    print(f"Enviando {len(vertices_np) // 2} segmentos diretamente para a VRAM (OpenGL)...")

    canvas = scene.SceneCanvas(keys='interactive', show=True, title="L-System GPU Acelerado", bgcolor='white')
    view = canvas.central_widget.add_view()
    view.camera = scene.PanZoomCamera(aspect=1)
    
    linha = scene.visuals.Line(
        pos=vertices_np, 
        color='black', 
        connect='segments', 
        antialias=False,
        parent=view.scene
    )
    
    view.camera.set_range(x=linha.bounds(0), y=linha.bounds(1))
    app.run()