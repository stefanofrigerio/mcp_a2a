"""
Agente Outdoor Activities - Valuta se si possono fare attività outdoor
Comunica con WeatherAgent tramite protocollo A2A
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import re
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OutdoorAgent:
    """Agente che valuta attività outdoor in base al meteo"""
    
    # Configurazione delle attività e condizioni meteo
    ACTIVITY_RULES = {
        "tagliare il prato": {
            "rain": False,
            "max_wind": 20,  # mph
            "min_temp": 45,  # F
            "max_temp": 95,
        },
        "dipingere": {
            "rain": False,
            "max_wind": 15,
            "min_temp": 50,
            "max_temp": 85,
            "humidity": "low"
        },
        "lavori stradali": {
            "rain": False,
            "max_wind": 25,
            "min_temp": 40,
            "max_temp": 100,
        },
        "costruzione": {
            "rain": False,
            "max_wind": 30,
            "min_temp": 32,
            "max_temp": 100,
        },
        "giardinaggio": {
            "rain": False,
            "max_wind": 20,
            "min_temp": 40,
            "max_temp": 90,
        }
    }
    
    def __init__(self, weather_agent):
        """
        Inizializza l'agente outdoor
        
        Args:
            weather_agent: Istanza di WeatherAgent per comunicazione A2A
        """
        self.name = "OutdoorAgent"
        self.weather_agent = weather_agent
        self.gemini_model = None
        self._setup_gemini()
        logger.info(f"✅ {self.name} inizializzato con protocollo A2A")
    
    def _setup_gemini(self):
        """Configura Gemini per l'agente"""
        genai.configure()
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def analyze_weather_for_activity(self, weather_data: dict, activity: str) -> dict:
        """
        Analizza i dati meteo per determinare se un'attività è fattibile
        
        Args:
            weather_data: Dati meteo dal WeatherAgent
            activity: Nome dell'attività
            
        Returns:
            Dict con valutazione e raccomandazioni
        """
        if not weather_data.get("success"):
            return {
                "can_do": False,
                "reason": "Impossibile ottenere dati meteo",
                "confidence": 0
            }
        
        forecast_text = weather_data.get("forecast", "")
        
        # Estrai condizioni meteo dal testo
        conditions = self._parse_weather_conditions(forecast_text)
        
        # Trova regole per l'attività
        rules = self._find_activity_rules(activity)
        
        # Valuta con Gemini
        prompt = f"""Analizza le seguenti previsioni meteo e determina se è possibile fare questa attività: "{activity}"

Previsioni meteo:
{forecast_text}

Condizioni meteo rilevate:
{conditions}

Linee guida per l'attività "{activity}" (da usare come riferimento, non come regole rigide):
{rules if rules else "Valuta in base al buon senso e alla sicurezza"}

IMPORTANTE:
- Usa il buon senso. Alcune attività (es. corsa) si possono fare con pioggia leggera, altre (es. giardinaggio) no.
- Valuta l'intensità dei fenomeni (es. pioggia leggera vs temporale).
- Se le condizioni violano leggermente le linee guida ma l'attività è comunque fattibile in sicurezza, puoi approvare (magari con avvertimenti).

Fornisci:
1. SI/NO se l'attività è fattibile
2. Motivazione dettagliata (spiega il perché basandoti sui dettagli meteo)
3. Consigli specifici
4. Livello di confidenza (0-100%)

Rispondi in italiano in modo chiaro e professionale."""

        response = self.gemini_model.generate_content(prompt)
        
        return {
            "activity": activity,
            "city": weather_data.get("city"),
            "analysis": response.text,
            "weather_data": conditions
        }
    
    def _parse_weather_conditions(self, forecast_text: str) -> dict:
        """Estrae condizioni meteo dal testo delle previsioni"""
        conditions = {
            "has_rain": any(word in forecast_text.lower() for word in ["rain", "shower", "storm", "pioggia"]),
            "has_snow": any(word in forecast_text.lower() for word in ["snow", "neve"]),
            "is_clear": any(word in forecast_text.lower() for word in ["clear", "sunny", "sereno", "sole"]),
        }
        
        # Estrai temperatura
        temp_match = re.search(r"Temperature:\s*(\d+)°F", forecast_text)
        if temp_match:
            conditions["temperature"] = int(temp_match.group(1))
        
        # Estrai vento
        wind_match = re.search(r"Wind:\s*(\d+)(?:\s*to\s*(\d+))?\s*mph", forecast_text)
        if wind_match:
            wind_speed = int(wind_match.group(2) if wind_match.group(2) else wind_match.group(1))
            conditions["wind_speed"] = wind_speed
        
        return conditions
    
    def _find_activity_rules(self, activity: str) -> dict:
        """Trova le regole per un'attività specifica"""
        activity_lower = activity.lower()
        
        for known_activity, rules in self.ACTIVITY_RULES.items():
            if known_activity in activity_lower:
                return rules
        
        return None
    
    def ask(self, question: str) -> str:
        """
        Gestisce domande sulle attività outdoor
        Protocollo A2A: chiede al WeatherAgent i dati meteo
        
        Args:
            question: Domanda dell'utente
            
        Returns:
            Risposta in linguaggio naturale
        """
        # Determina se la domanda riguarda attività outdoor
        if not self._is_outdoor_activity_question(question):
            # Delega al WeatherAgent
            logger.info("Domanda delegata al WeatherAgent")
            return self.weather_agent.ask(question)
        
        # Estrai città e attività dalla domanda
        city = self._extract_city(question)
        activity = self._extract_activity(question)
        
        if not city:
            return "Per favore specifica una città per la quale vuoi conoscere le condizioni meteo."
        
        logger.info(f"📡 A2A: OutdoorAgent richiede dati meteo a WeatherAgent per {city}")
        
        # Protocollo A2A: chiedi dati al WeatherAgent
        weather_data = self.weather_agent.get_weather(city)
        
        logger.info(f"📡 A2A: WeatherAgent ha risposto con successo={weather_data.get('success')}")
        
        # Verifica che abbiamo dati meteo validi
        if not weather_data.get("success"):
            error_msg = weather_data.get("error", "Impossibile ottenere dati meteo")
            return f"Mi dispiace, non posso valutare le condizioni per le attività outdoor perché: {error_msg}"
        
        # Analizza per l'attività specifica
        if activity:
            analysis = self.analyze_weather_for_activity(weather_data, activity)
        else:
            # Analisi generica per lavori outdoor
            analysis = self.analyze_weather_for_activity(weather_data, "lavori outdoor generici")
        
        # Restituisci l'analisi se presente
        if "analysis" in analysis:
            return analysis["analysis"]
        else:
            return f"Mi dispiace, si è verificato un errore nell'analisi: {analysis.get('reason', 'Errore sconosciuto')}"
    
    def _is_outdoor_activity_question(self, question: str) -> bool:
        """Determina se la domanda riguarda attività outdoor"""
        outdoor_keywords = [
            "posso", "potrei", "dovrei", "fare", "lavori", "tagliare", "prato",
            "dipingere", "costruire", "giardinaggio", "outdoor", "esterno",
            "lavoro", "attività"
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in outdoor_keywords)
    
    def _extract_city(self, question: str) -> str:
        """Estrae il nome della città dalla domanda"""
        # Pattern comuni: "a Roma", "in Milano", "per New York"
        patterns = [
            r"(?:a|in|per)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\?"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_activity(self, question: str) -> str:
        """Estrae l'attività dalla domanda"""
        question_lower = question.lower()
        
        for activity in self.ACTIVITY_RULES.keys():
            if activity in question_lower:
                return activity
        
        # Cerca altre attività comuni
        if "dipingere" in question_lower or "verniciare" in question_lower:
            return "dipingere"
        if "costruire" in question_lower or "costruzione" in question_lower:
            return "costruzione"
        
        return None

