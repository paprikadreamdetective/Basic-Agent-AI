from flask import Flask, request, jsonify
from flask_cors import CORS
from uagents_core.crypto import Identity
#from fetchai.communication import send_message_to_agent
from fetchai.registration import register_with_agentverse

from fetchai.communication import parse_message_from_agent, send_message_to_agent
from dotenv import load_dotenv
import logging
import os

import threading
import queue
import time

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_SECRET_KEY_2="otra_clave_secreta"

load_dotenv()



AGENTVERSE_API_KEY = os.getenv('AGENTVERSE_API_KEY')

SERVER_AGENT_ADDRESS = os.getenv('SERVER_AGENT_ADDRESS')




# Flask app
app = Flask(__name__)
CORS(app)

response_queue = queue.Queue()

client_identity = None

def init_client():
    global client_identity
    
    try:
        client_identity = Identity.from_seed(AGENT_SECRET_KEY_2, 0)
        logger.info(f"Agente cliente iniciado: {client_identity.address}")

        readme = """
        ![domain:innovation-lab](https://img.shields.io/badge/innovation--lab-3D8BD3)
        domain:asi1

        <description>Este agente envía preguntas al agente ASI1 y recibe respuestas.</description>
        <use_cases>
            <use_case>Enviar preguntas al agente ASI1.</use_case>
        </use_cases>
        <payload_requirements>
            <description>Enviar preguntas como texto.</description>
            <payload>
                <requirement>
                    <parameter>query</parameter>
                    <description>Texto de la pregunta.</description>
                </requirement>
            </payload>
        </payload_requirements>
        """

        register_with_agentverse(
            identity=client_identity,
            url="http://localhost:5055/api/webhook",
            agentverse_token=AGENTVERSE_API_KEY,
            agent_title="ASI1 Client Agent",
            readme=readme
        )

    except Exception as e:
        logger.error(f"Error al registrar agente: {e}")
        raise

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        query = data.get("query")

        if not query:
            return jsonify({"error": "Missing query"}), 400

        logger.info(f"Consulta recibida del frontend: {query}")

        # Enviar mensaje al agente
        send_message_to_agent(
            client_identity,
            SERVER_AGENT_ADDRESS,
            {"query": query}
        )

        
        for _ in range(20):  
            try:
                response = response_queue.get_nowait()
                return jsonify({"response": response})
            except queue.Empty:
                time.sleep(0.5)

        return jsonify({"error": "Timeout esperando respuesta del agente"}), 504

    except Exception as e:
        logger.error(f"Error en /api/chat: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_data().decode("utf-8")
        logger.info("Mensaje recibido en webhook cliente")

        message = parse_message_from_agent(data)
        response = message.payload.get("response", "")

        logger.info(f"Respuesta del servidor: {response}")

        response_queue.put(response)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Error procesando respuesta en el cliente: {e}")
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    init_client()
    app.run(host='0.0.0.0', port=5055)

