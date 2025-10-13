#!/usr/bin/env python3
"""
Main per ottenere le previsioni del tempo per una città degli USA
Usa il client Gemini con il server MCP weather
"""

import sys
import os
import argparse
import logging

# Aggiungi il percorso src al PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from client.gemini_client import GeminiClient

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Funzione principale per ottenere le previsioni del tempo"""
    parser = argparse.ArgumentParser(
        description='Ottieni le previsioni del tempo per una città degli USA',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python weather_main.py --city "San Francisco"
  python weather_main.py --city "New York"
  python weather_main.py --city "Los Angeles"
        """
    )
    
    parser.add_argument(
        '--city', '-c',
        type=str,
        help='Nome della città degli USA per cui ottenere le previsioni del tempo'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostra output dettagliato'
    )
    
    args = parser.parse_args()
    
    # Verifica che la città sia specificata
    if not args.city:
        print("❌ Errore: Manca la città!")
        print("Usa --city o -c per specificare la città degli USA")
        print("Esempio: python weather_main.py --city 'San Francisco'")
        sys.exit(1)
    
    # Configura logging verboso se richiesto
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print(f"🌤️  Richiesta previsioni per: {args.city}")
    print("=" * 50)
    
    # Crea e configura il client
    client = GeminiClient()
    
    try:
        # Configura Gemini con autenticazione gcloud
        print("🔧 Configurazione Gemini...")
        client.setup_gemini(use_gcloud_auth=True)
        
        # Avvia server MCP
        print("🚀 Avvio server MCP...")
        client.start_mcp_server()
        
        # Inizializza MCP
        print("🔗 Inizializzazione MCP...")
        client.initialize_mcp()
        
        # Ottieni le previsioni
        print(f"📡 Richiesta previsioni per {args.city}...")
        
        # Crea il prompt per Gemini
        prompt = f"Dimmi le previsioni del tempo per {args.city}, USA. Usa i tool MCP disponibili per ottenere le informazioni meteorologiche."
        
        # Invia la richiesta a Gemini
        response = client.gemini_model.generate_content(prompt)
        
        print("\n📋 Previsioni del tempo:")
        print("-" * 30)
        print(response.text)
        print("-" * 30)
        
        print("\n✅ Previsioni ottenute con successo!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Operazione interrotta dall'utente")
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        # Pulisci le risorse
        print("\n🧹 Pulizia risorse...")
        client.cleanup()

if __name__ == "__main__":
    main()
