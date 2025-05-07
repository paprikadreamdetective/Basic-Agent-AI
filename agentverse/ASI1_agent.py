from flask import Flask, request, jsonify
from flask_cors import CORS
from uagents_core.crypto import Identity
from fetchai.registration import register_with_agentverse
from fetchai.communication import parse_message_from_agent, send_message_to_agent
import logging
import requests
import os
from dotenv import load_dotenv

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Claves y tokens

ASI1_API_KEY = os.getenv('ASI1_API_KEY')
AGENT_SECRET_KEY = os.getenv('AGENT_SECRET_KEY_1')

AGENTVERSE_API_KEY = str(os.getenv('AGENTVERSE_API_KEY'))
print("agent verse key: ")
# Flask app
app = Flask(__name__)
CORS(app)

# Identidad del agente
client_identity = None

# API de ASI1
def get_asi1_response(query: str) -> str:
    
    api_key = ASI1_API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "asi1-mini",
        "messages": [
            {
                "role": "system",
                "content": "Eres un asistente que ayuda a encontrar la ruta de una ciudad A a una ciudad B, responde en formato de informe. Incluye: carretera, casetas, cobros, tiempo estimado. Que sea breve"
            },
            {"role": "user", "content": query}
        ]
    }

    try:
        response = requests.post("https://api.asi1.ai/v1/chat/completions", json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                return "La API de ASI1 devolvió una respuesta vacía."
        else:
            return f"Error de ASI1 API: {response.status_code}, {response.text}"
    except Exception as e:
        return f"Error al conectar con la API de ASI1: {str(e)}"

# Inicializa y registra el agente en AgentVerse
def init_client():
    global client_identity
    try:
        client_identity = Identity.from_seed(AGENT_SECRET_KEY, 0)
        logger.info(f"Agente iniciado con dirección: {client_identity.address}")

        readme = """
        ![domain:routes](https://img.shields.io/badge/route-assistant-blue)
        domain:routing-helper

        <description>Este agente responde con rutas óptimas entre ciudades en México.</description>
        <use_cases>
            <use_case>Obtener rutas entre dos ciudades.</use_case>
        </use_cases>
        <payload_requirements>
        <description>Requiere una consulta tipo texto con la ciudad origen y destino.</description>
        <payload>
            <requirement>
                <parameter>message</parameter>
                <description>Consulta de ruta a procesar.</description>
            </requirement>
        </payload>
        </payload_requirements>
        """

        register_with_agentverse(
            identity=client_identity,
            url="http://localhost:5002/api/webhook",
            agentverse_token=AGENTVERSE_API_KEY,
            agent_title="ASI1 Flask Routing Agent",
            readme=readme
        )

        logger.info("Registro del agente en AgentVerse completado.")
    except Exception as e:
        logger.error(f"Error al inicializar agente: {e}")
        raise

# Endpoint que recibe mensajes de otros agentes
@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_data().decode("utf-8")
        logger.info("Mensaje recibido en webhook")

        message = parse_message_from_agent(data)
        #user_query = message.payload.strip()
        user_query = message.payload["query"].strip()

        logger.info(f"Consulta recibida: {user_query}")

        # Procesar la consulta con ASI1
        asi1_result = get_asi1_response(user_query)

        logger.info(f"Respuesta generada: {asi1_result}")

        # Responder al agente emisor
        print(f"Contenido del mensaje: {message}")

        send_message_to_agent(client_identity, message.sender, {"response": asi1_result})

        return jsonify({"status": "success", "data": asi1_result})

    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        return jsonify({"error": str(e)}), 500

# Iniciar servidor Flask
if __name__ == "__main__":
    init_client()
    app.run(host="0.0.0.0", port=5002)

