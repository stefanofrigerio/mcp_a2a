"""
Agente Weather - Gestisce previsioni meteorologiche
Utilizza il client Gemini + MCP per ottenere dati meteo
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.gemini_client import GeminiClient
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherAgent:
    """Agente specializzato per previsioni meteorologiche"""
    
    def __init__(self):
        """Inizializza l'agente weather"""
        self.name = "WeatherAgent"
        self.client = None
        self.initialized = False
        
    def initialize(self):
        """Inizializza il client Gemini + MCP"""
        if not self.initialized:
            self.client = GeminiClient()
            self.client.setup_gemini(use_gcloud_auth=True)
            self.client.start_mcp_server()
            self.client.initialize_mcp()
            self.initialized = True
            logger.info(f"✅ {self.name} inizializzato")
    
    def get_weather(self, city: str) -> Dict[str, Any]:
        """
        Ottiene le previsioni meteo per una città
        
        Args:
            city: Nome della città
            
        Returns:
            Dict con informazioni meteo strutturate
        """
        if not self.initialized:
            self.initialize()
        
        try:
            # Ottieni coordinate
            coords_result = self.client.call_mcp_tool("get_coordinates", {"city": city})
            
            # Estrai coordinate
            import re
            lat_match = re.search(r"Latitudine:\s*([\d.]+)", coords_result)
            lon_match = re.search(r"Longitudine:\s*([\d.-]+)", coords_result)
            
            if not lat_match or not lon_match:
                return {
                    "success": False,
                    "error": "Impossibile trovare le coordinate",
                    "city": city
                }
            
            latitude = float(lat_match.group(1))
            longitude = float(lon_match.group(1))  # Prende solo il primo gruppo
            
            # Ottieni previsioni
            forecast_result = self.client.call_mcp_tool("get_forecast", {
                "latitude": latitude,
                "longitude": longitude
            })
            
            return {
                "success": True,
                "city": city,
                "coordinates": {"latitude": latitude, "longitude": longitude},
                "forecast": forecast_result,
                "raw_data": forecast_result
            }
            
        except Exception as e:
            logger.error(f"Errore in get_weather: {e}")
            return {
                "success": False,
                "error": str(e),
                "city": city
            }
    
    def ask(self, question: str) -> str:
        """
        Interfaccia conversazionale per domande sul meteo
        
        Args:
            question: Domanda dell'utente
            
        Returns:
            Risposta in linguaggio naturale
        """
        if not self.initialized:
            self.initialize()
        
        return self.client.chat_with_tools(question)
    
    def close(self):
        """Chiude le connessioni"""
        if self.client:
            self.client.close()
            logger.info(f"✅ {self.name} chiuso")

