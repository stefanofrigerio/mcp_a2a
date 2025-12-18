"""
Coordinatore A2A (Agent-to-Agent)
Gestisce la comunicazione tra WeatherAgent e OutdoorAgent
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.weather_agent import WeatherAgent
from agents.outdoor_agent import OutdoorAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class A2ACoordinator:
    """Coordinatore per comunicazione Agent-to-Agent"""
    
    def __init__(self):
        """Inizializza il coordinatore e gli agenti"""
        self.name = "A2ACoordinator"
        
        logger.info("🚀 Inizializzazione sistema A2A")
        
        # Inizializza WeatherAgent
        self.weather_agent = WeatherAgent()
        self.weather_agent.initialize()
        
        # Inizializza OutdoorAgent con riferimento al WeatherAgent
        self.outdoor_agent = OutdoorAgent(self.weather_agent)
        
        logger.info("✅ Sistema A2A inizializzato con 2 agenti")
    
    def process_query(self, question: str) -> str:
        """
        Processa una domanda e determina quale agente deve gestirla
        
        Args:
            question: Domanda dell'utente
            
        Returns:
            Risposta elaborata dall'agente appropriato
        """
        logger.info(f"📥 Query ricevuta: {question}")
        
        # L'OutdoorAgent sa determinare se deve gestire la domanda
        # o delegarla al WeatherAgent
        response = self.outdoor_agent.ask(question)
        
        return response
    
    def get_weather(self, city: str) -> dict:
        """
        Accesso diretto al WeatherAgent
        
        Args:
            city: Nome della città
            
        Returns:
            Dati meteo strutturati
        """
        return self.weather_agent.get_weather(city)
    
    def close(self):
        """Chiude tutti gli agenti"""
        self.weather_agent.close()
        logger.info("✅ Sistema A2A chiuso")


def main():
    """Test del sistema A2A"""
    coordinator = A2ACoordinator()
    
    try:
        print("\n" + "="*60)
        print("🤖 Sistema A2A - Weather + Outdoor Activities")
        print("="*60)
        
        # Test 1: Domanda solo meteo
        print("\n📋 Test 1: Solo meteo")
        print("-" * 60)
        response = coordinator.process_query("Che tempo fa a New York?")
        print(f"\nRisposta:\n{response[:400]}...")
        
        # Test 2: Domanda attività outdoor
        print("\n📋 Test 2: Attività outdoor")
        print("-" * 60)
        response = coordinator.process_query("Posso tagliare il prato domani a San Francisco?")
        print(f"\nRisposta:\n{response[:400]}...")
        
        # Test 3: Lavori stradali
        print("\n📋 Test 3: Lavori stradali")
        print("-" * 60)
        response = coordinator.process_query("Domani posso fare lavori stradali a New York?")
        print(f"\nRisposta:\n{response[:400]}...")
        
        print("\n" + "="*60)
        print("✅ Test completati")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Errore: {e}")
        import traceback
        traceback.print_exc()
    finally:
        coordinator.close()


if __name__ == "__main__":
    main()

