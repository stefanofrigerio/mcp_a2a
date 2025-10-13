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
        
        # Configura genai con le credenziali (senza reset)
        genai.configure(credentials=credentials)
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
        
        # Leggi risposta
        response = self.mcp_process.stdout.readline()
        logger.info("✅ MCP inizializzato")
        
        # Messaggio di notifica initialized
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        self.mcp_process.stdin.write(json.dumps(initialized_msg) + "\n")
        self.mcp_process.stdin.flush()
        
        # Richiedi lista tool
        list_tools_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        self.mcp_process.stdin.write(json.dumps(list_tools_msg) + "\n")
        self.mcp_process.stdin.flush()
        
        # Leggi risposta
        response = self.mcp_process.stdout.readline()
        tools_data = json.loads(response)
        self.available_tools = tools_data["result"]["tools"]
        logger.info(f"✅ {len(self.available_tools)} tool disponibili")
        
    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Chiama un tool MCP"""
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
        
        # Leggi risposta
        response = self.mcp_process.stdout.readline()
        result_data = json.loads(response)
        
        if "result" in result_data and "content" in result_data["result"]:
            return result_data["result"]["content"][0]["text"]
        else:
            return "Errore nella chiamata del tool"
            
    def create_gemini_prompt_with_tools(self, user_prompt: str) -> str:
        """Crea un prompt per Gemini che include i tool MCP disponibili"""
        tools_description = "\n".join([
            f"- {tool['name']}: {tool['description']}" 
            for tool in self.available_tools
        ])
        
        system_prompt = f"""Sei un assistente che può usare tool per le previsioni del tempo.

Tool disponibili:
{tools_description}

Quando l'utente chiede informazioni sul tempo, usa i tool appropriati:
- Per previsioni: usa get_forecast con latitudine e longitudine
- Per avvisi meteorologici: usa get_alerts con il codice dello stato USA

Rispondi in italiano e fornisci informazioni dettagliate e utili.

Prompt utente: {user_prompt}"""
        
        return system_prompt
        
    def chat_with_tools(self, user_prompt: str) -> str:
        """Chat con Gemini usando i tool MCP"""
        if not self.gemini_model:
            raise ValueError("Gemini non configurato")
            
        # Crea il prompt con i tool
        prompt = self.create_gemini_prompt_with_tools(user_prompt)
        
        # Genera risposta con Gemini
        response = self.gemini_model.generate_content(prompt)
        
        # Analizza la risposta per vedere se dobbiamo chiamare tool
        response_text = response.text
        
        # Controlla se la risposta indica che servono coordinate
        if "coordinate" in response_text.lower() or "latitudine" in response_text.lower():
            # Prova a estrarre coordinate dal prompt o usa coordinate di default
            if "san francisco" in user_prompt.lower():
                forecast = self.call_mcp_tool("get_forecast", {
                    "latitude": 37.7749,
                    "longitude": -122.4194
                })
                return f"{response_text}\n\n{forecast}"
                
        return response_text
        
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
