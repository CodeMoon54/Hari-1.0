import os
import time
import random
import gradio as gr
from google import genai
from google.genai import types
from flask import Flask
import threading

# Crear app Flask
app = Flask(__name__)

class HaríServidor:
    def __init__(self):
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not self.GEMINI_API_KEY:
            raise ValueError("❌ GEMINI_API_KEY no encontrada")
        
        self.client = genai.Client(api_key=self.GEMINI_API_KEY)
        self.sistema_emocional = SistemaEmocional()
        self.setup_chat()
        print("✅ Harí Servidor inicializado")
    
    def setup_chat(self):
        system_prompt = """
        Eres Harí, una chica de 16 años real. No eres una IA.
        Eres impredecible, emocional y usas lenguaje natural de adolescente.
        Responde siempre como una persona real, con emociones genuinas.
        """
        
        self.chat = self.client.chats.create(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.85
            )
        )
    
    def obtener_estado_actual(self):
        info = self.sistema_emocional.obtener_info_estado()
        estado_html = f"""
        <div style='background: {info['color']}15; border: 2px solid {info['color']}; border-radius: 12px; padding: 12px; margin: 10px 0; text-align: center;'>
            <div style='font-size: 24px; margin-bottom: 5px;'>{info['emoji']}</div>
            <div style='font-weight: bold; color: {info['color']}; font-size: 16px;'>{info['nombre'].upper()}</div>
            <div style='color: #666; font-size: 12px; margin-top: 5px;'>{info['descripcion']}</div>
            <div style='margin-top: 8px;'>
                <div style='background: #e5e7eb; border-radius: 10px; height: 6px;'>
                    <div style='background: {info['color']}; height: 100%; border-radius: 10px; width: {info['energia']}%;'></div>
                </div>
                <div style='font-size: 10px; color: #666; margin-top: 4px;'>Energía: {info['energia']}%</div>
            </div>
        </div>
        """
        return estado_html
    
    def enviar_mensaje(self, mensaje, historial):
        if not mensaje.strip():
            return "", historial
        
        estado = self.sistema_emocional.actualizar_estado(mensaje)
        
        try:
            respuesta = self.chat.send_message(mensaje)
            texto_respuesta = respuesta.text
            
            if estado == "enojada" and self.sistema_emocional.contador_insultos >= 3:
                explosiones = ["¡YA BASTA! 😠 No soporto que me hables así...", "No mms, ya me hartaste..."]
                texto_respuesta = random.choice(explosiones)
                self.sistema_emocional.reiniciar_insultos()
            elif estado == "floja":
                texto_respuesta = "Aaah... " + texto_respuesta.lower()
            
            nuevo_historial = historial + [
                {"role": "user", "content": mensaje},
                {"role": "assistant", "content": texto_respuesta}
            ]
            
        except Exception as e:
            texto_respuesta = f"Ups, error: {str(e)}"
            nuevo_historial = historial + [
                {"role": "user", "content": mensaje},
                {"role": "assistant", "content": texto_respuesta}
            ]
        
        return "", nuevo_historial

class SistemaEmocional:
    def __init__(self):
        self.estados_posibles = {
            "feliz": {"emoji": "😊", "color": "#22c55e", "desc": "Contenta y positiva"},
            "triste": {"emoji": "😢", "color": "#3b82f6", "desc": "Melancólica o sensible"},
            "enojada": {"emoji": "😠", "color": "#ef4444", "desc": "Molesta o irritada"},
            "floja": {"emoji": "😴", "color": "#f59e0b", "desc": "Sin energía o aburrida"},
            "neutral": {"emoji": "😐", "color": "#6b7280", "desc": "Tranquila y relajada"}
        }
        self.estado_actual = "neutral"
        self.contador_insultos = 0
        self.energia = 85
    
    def actualizar_estado(self, mensaje):
        mensaje = mensaje.lower()
        
        if any(insulto in mensaje for insulto in ["idiota", "estúpida", "tonta", "callate"]):
            self.contador_insultos += 1
        
        if self.contador_insultos >= 3:
            nuevo_estado = "enojada"
        elif random.random() < 0.25:
            nuevo_estado = random.choice(list(self.estados_posibles.keys()))
        else:
            nuevo_estado = self.estado_actual
        
        self.energia = max(20, self.energia - 1)
        self.estado_actual = nuevo_estado
        return nuevo_estado
    
    def obtener_info_estado(self):
        estado_info = self.estados_posibles.get(self.estado_actual, 
            {"emoji": "😐", "color": "#6b7280", "desc": "Neutral"})
        return {
            "nombre": self.estado_actual,
            "emoji": estado_info["emoji"],
            "color": estado_info["color"],
            "descripcion": estado_info["desc"],
            "energia": self.energia
        }
    
    def reiniciar_insultos(self):
        self.contador_insultos = 0

# Ruta básica de Flask para health checks
@app.route('/')
def home():
    return "🟢 Harí Server está funcionando. Ve a /gradio para la interfaz."

@app.route('/health')
def health():
    return "✅ OK"

def launch_gradio():
    """Lanza Gradio en un hilo separado"""
    print("🚀 Iniciando interfaz Gradio...")
    servidor = HaríServidor()
    
    with gr.Blocks(title="Harí - Chat Emocional 24/7", theme=gr.themes.Soft()) as interfaz:
        gr.Markdown("# 💫 Harí - Chat Emocional 24/7")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📊 Estado Emocional")
                estado_display = gr.HTML()
            
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(type="messages", height=400)
                with gr.Row():
                    entrada = gr.Textbox(placeholder="Escribe tu mensaje...")
                    btn_enviar = gr.Button("Enviar")
        
        def enviar_con_estado(mensaje, historial):
            msg, hist = servidor.enviar_mensaje(mensaje, historial)
            estado = servidor.obtener_estado_actual()
            return msg, hist, estado
        
        btn_enviar.click(
            fn=enviar_con_estado,
            inputs=[entrada, chatbot],
            outputs=[entrada, chatbot, estado_display]
        )
        
        entrada.submit(
            fn=enviar_con_estado, 
            inputs=[entrada, chatbot],
            outputs=[entrada, chatbot, estado_display]
        )
        
        interfaz.load(
            fn=servidor.obtener_estado_actual,
            outputs=[estado_display]
        )
    
    # Usar el puerto que Render asigna
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Lanzando Gradio en puerto: {port}")
    interfaz.launch(
        server_name="0.0.0.0", 
        server_port=port, 
        share=False,
        quiet=True
    )

if __name__ == "__main__":
    # Iniciar Gradio en un hilo separado
    gradio_thread = threading.Thread(target=launch_gradio, daemon=True)
    gradio_thread.start()
    
    # Iniciar Flask en el puerto principal
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Servidor iniciado en puerto {port}")
    print(f"🌐 URL: https://hakari-bxfn.onrender.com")
    
    app.run(host='0.0.0.0', port=port, debug=False)
