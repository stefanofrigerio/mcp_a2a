#!/usr/bin/env python3
"""
Client Gemini funzionante con MCP
"""
import asyncio
import subprocess
import json
import logging
import os
from typing import Any, Dict, List, Optional

import google.generativeai as genai

# Configura logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiClient:
    """Client Gemini funzionante con MCP"""
    
    def __init__(self):
        """Inizializza il client Gemini"""
        self.gemini_model = None
        self.mcp_process = None
        self.available_tools = []
        
    def setup_gemini(self, use_gcloud_auth: bool = True):
        """Configura Gemini con autenticazione gcloud"""
        # Usa solo Application Default Credentials (ADC) da gcloud
        import google.auth
        credentials, project = google.auth.default()
        
        # Configura genai senza specificare credentials (usa ADC automaticamente)
        genai.configure()
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        logger.info(f"✅ Gemini configurato con autenticazione gcloud (progetto: {project})")
        
        
    def start_mcp_server(self):
        """Avvia il server MCP"""
        self.mcp_process = subprocess.Popen(
            ["poetry", "run", "python", "src/server/mcp_weather.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/Users/frigeri2/projects/mcp_a2a"
        )
        logger.info("✅ Server MCP avviato")
        
    def initialize_mcp(self):
        """Inizializza la comunicazione MCP"""
        try:
            # Messaggio di inizializzazione
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "gemini-client", "version": "1.0"}
                }
            }
            
            self.mcp_process.stdin.write(json.dumps(init_msg) + "\n")
            self.mcp_process.stdin.flush()
            
            # Leggi risposta con timeout
            import select
            import time
            time.sleep(0.2)  # Piccola pausa per permettere al server di rispondere
            ready, _, _ = select.select([self.mcp_process.stdout], [], [], 5.0)
            if ready:
                response = self.mcp_process.stdout.readline()
                logger.info("✅ MCP inizializzato")
                
                # Messaggio di notifica initialized
                initialized_msg = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                
                self.mcp_process.stdin.write(json.dumps(initialized_msg) + "\n")
                self.mcp_process.stdin.flush()
                
                # Piccola pausa prima di richiedere la lista tool
                time.sleep(0.2)
                
                # Richiedi lista tool
                list_tools_msg = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }
                
                self.mcp_process.stdin.write(json.dumps(list_tools_msg) + "\n")
                self.mcp_process.stdin.flush()
                
                # Leggi risposta con timeout
                time.sleep(0.2)
                ready, _, _ = select.select([self.mcp_process.stdout], [], [], 5.0)
                if ready:
                    response = self.mcp_process.stdout.readline()
                    tools_data = json.loads(response)
                    if "result" in tools_data and "tools" in tools_data["result"]:
                        self.available_tools = tools_data["result"]["tools"]
                        logger.info(f"✅ {len(self.available_tools)} tool disponibili")
                    else:
                        logger.warning(f"Risposta inattesa: {response}")
                        self.available_tools = []
                else:
                    logger.error("Timeout nella lettura della lista tool")
                    self.available_tools = []
            else:
                logger.error("Timeout nell'inizializzazione MCP")
                self.available_tools = []
                
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione MCP: {e}")
            self.available_tools = []
        
    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Chiama un tool MCP"""
        try:
            import select
            import time
            
            call_tool_msg = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            self.mcp_process.stdin.write(json.dumps(call_tool_msg) + "\n")
            self.mcp_process.stdin.flush()
            
            # Aspetta e leggi risposta con timeout
            time.sleep(0.2)
            ready, _, _ = select.select([self.mcp_process.stdout], [], [], 30.0)
            if ready:
                response = self.mcp_process.stdout.readline()
                result_data = json.loads(response)
                
                if "result" in result_data and "content" in result_data["result"]:
                    return result_data["result"]["content"][0]["text"]
                elif "error" in result_data:
                    error_msg = result_data["error"].get("message", "Errore sconosciuto")
                    logger.error(f"Errore tool MCP: {error_msg}")
                    return f"Errore: {error_msg}"
                else:
                    logger.warning(f"Risposta inattesa dal tool: {response}")
                    return "Errore: risposta inattesa dal tool"
            else:
                logger.error("Timeout nella chiamata tool")
                return "Errore: timeout nella chiamata tool"
        except Exception as e:
            logger.error(f"Errore nella chiamata tool {tool_name}: {e}")
            return f"Errore: {str(e)}"
            
    def create_gemini_prompt_with_tools(self, user_prompt: str) -> str:
        """Crea un prompt per Gemini che include i tool MCP disponibili"""
        tools_description = "\n".join([
            f"- {tool['name']}: {tool['description']}" 
            for tool in self.available_tools
        ])
        
        system_prompt = f"""Sei un assistente che può usare tool per le previsioni del tempo.

Tool disponibili:
{tools_description}

Quando l'utente chiede informazioni sul tempo, usa i tool appropriati in questo ordine:
1. Se l'utente menziona una città senza coordinate, usa prima get_coordinates per ottenere latitudine e longitudine
2. Usa get_forecast con le coordinate per ottenere le previsioni
3. Per avvisi meteorologici negli USA: usa get_alerts con il codice dello stato USA

Esempio di workflow:
- Utente: "Che tempo fa a Roma?"
  1. Chiama get_coordinates("Roma") per ottenere le coordinate
  2. Chiama get_forecast con le coordinate ottenute
  3. Fornisci una risposta completa e dettagliata

Rispondi sempre in italiano e fornisci informazioni dettagliate e utili.

Prompt utente: {user_prompt}"""
        
        return system_prompt
        
    def extract_city_name(self, text: str) -> str | None:
        """Estrae il nome di una città dal testo"""
        # Cerca pattern comuni per città
        import re
        # Pattern per "a Roma", "a Milano", "a New York", etc.
        patterns = [
            r"a\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"per\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def chat_with_tools(self, user_prompt: str) -> str:
        """Chat con Gemini usando i tool MCP"""
        if not self.gemini_model:
            raise ValueError("Gemini non configurato")
        
        # Prima, controlla se serve chiamare get_coordinates
        city = self.extract_city_name(user_prompt)
        coordinates = None
        coords_result = None
        
        if city:
            logger.info(f"Città rilevata: {city}")
            try:
                # Ottieni le coordinate della città
                coords_result = self.call_mcp_tool("get_coordinates", {"city": city})
                logger.info(f"Coordinate ottenute: {coords_result}")
                
                # Estrai latitudine e longitudine dal risultato
                import re
                lat_match = re.search(r"Latitudine:\s*([\d.]+)", coords_result)
                lon_match = re.search(r"Longitudine:\s*([\d.-]+)", coords_result)
                
                if lat_match and lon_match:
                    coordinates = {
                        "latitude": float(lat_match.group(1)),
                        "longitude": float(lon_match.group(1))
                    }
                    logger.info(f"Coordinate estratte: lat={coordinates['latitude']}, lon={coordinates['longitude']}")
            except Exception as e:
                logger.error(f"Errore nel recupero coordinate: {e}")
        
        # Se abbiamo le coordinate, ottieni le previsioni
        if coordinates and ("tempo" in user_prompt.lower() or "prevision" in user_prompt.lower()):
            try:
                logger.info(f"Chiamata get_forecast con coordinate: {coordinates}")
                forecast = self.call_mcp_tool("get_forecast", coordinates)
                logger.info(f"Previsioni ottenute: {forecast[:200]}...")
                # Crea un prompt con le informazioni ottenute
                enhanced_prompt = f"{user_prompt}\n\nHo già ottenuto le seguenti informazioni:\n\n{coords_result}\n\n{forecast}\n\nFornisci una risposta completa e dettagliata in italiano."
            except Exception as e:
                logger.error(f"Errore nel recupero previsioni: {e}")
                import traceback
                logger.error(traceback.format_exc())
                enhanced_prompt = f"{user_prompt}\n\nHo ottenuto le coordinate: {coords_result}\n\nMa non sono riuscito a ottenere le previsioni meteo. Potresti spiegare all'utente che le previsioni meteo sono disponibili solo per gli Stati Uniti d'America, e suggerire fonti alternative per città fuori dagli USA."
        else:
            # Usa il prompt normale con i tool
            enhanced_prompt = self.create_gemini_prompt_with_tools(user_prompt)
        
        # Genera risposta con Gemini
        response = self.gemini_model.generate_content(enhanced_prompt)
        return response.text
        
    def close(self):
        """Chiudi le connessioni"""
        if self.mcp_process:
            self.mcp_process.terminate()
            self.mcp_process.wait()
            logger.info("✅ Server MCP terminato")
    
    def cleanup(self):
        """Pulisce le risorse (alias per close)"""
        self.close()

def main():
    """Funzione principale per testare il client"""
    client = GeminiClient()
    
    try:
        # Configura Gemini con autenticazione gcloud
        print("Configurazione Gemini...")
        print("Usando autenticazione gcloud (Application Default Credentials)")
        client.setup_gemini(use_gcloud_auth=True)
        
        # Avvia server MCP
        print("Avvio server MCP...")
        client.start_mcp_server()
        
        # Inizializza MCP
        client.initialize_mcp()
        
        # Test chat
        print("\n🤖 Client Gemini + MCP pronto!")
        print("Digita 'quit' per uscire")
        
        while True:
            user_input = input("\nTu: ").strip()
            if user_input.lower() == 'quit':
                break
                
            if user_input:
                response = client.chat_with_tools(user_input)
                print(f"🤖 Gemini: {response}")
                
    except Exception as e:
        logger.error(f"Errore: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
