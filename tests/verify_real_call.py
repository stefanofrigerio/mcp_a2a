import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.outdoor_agent import OutdoorAgent

def verify_nuance():
    # Mock Weather Agent
    mock_weather = MagicMock()
    agent = OutdoorAgent(mock_weather)
    
    # Scenario: Light Rain
    weather_data = {
        "success": True,
        "forecast": "Light rain showers, 65°F, wind 5mph",
        "city": "TestCity"
    }
    
    print("\n--- TEST 1: Giardinaggio con pioggia leggera ---")
    result_gardening = agent.analyze_weather_for_activity(weather_data, "giardinaggio")
    print(result_gardening["analysis"])
    
    print("\n--- TEST 2: Corsa con pioggia leggera ---")
    result_running = agent.analyze_weather_for_activity(weather_data, "corsa")
    print(result_running["analysis"])

if __name__ == "__main__":
    verify_nuance()
