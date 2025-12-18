"""
Frontend FastAPI per il sistema meteorologico con Gemini + MCP
"""
import sys
from pathlib import Path

# Aggiungi il percorso src al path per importare i moduli
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
from typing import Optional
import logging

from client.gemini_client import GeminiClient
from agents.a2a_coordinator import A2ACoordinator

# Configura logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crea l'app FastAPI
app = FastAPI(title="Weather Assistant", description="Sistema meteorologico con Gemini + MCP + A2A")

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Coordinatore A2A globale
a2a_coordinator: Optional[A2ACoordinator] = None


def get_coordinator() -> A2ACoordinator:
    """Ottiene o crea il coordinatore A2A"""
    global a2a_coordinator
    if a2a_coordinator is None:
        a2a_coordinator = A2ACoordinator()
        logger.info("✅ Coordinatore A2A inizializzato")
    return a2a_coordinator


@app.on_event("shutdown")
async def shutdown_event():
    """Chiude le connessioni alla chiusura dell'app"""
    global a2a_coordinator
    if a2a_coordinator:
        a2a_coordinator.close()
        logger.info("✅ Coordinatore A2A chiuso")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Pagina principale con il form"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/ask", response_class=HTMLResponse)
async def ask_weather(request: Request, city: str = Form(...), question_type: str = Form("weather")):
    """Gestisce la richiesta di previsioni meteo o attività outdoor"""
    try:
        coordinator = get_coordinator()
        
        # Costruisci la domanda basata sul tipo
        if question_type == "outdoor":
            question = f"Posso fare lavori outdoor oggi a {city}?"
        else:
            question = f"Che tempo fa oggi a {city}?"
        
        logger.info(f"Richiesta: '{question}' (tipo: {question_type})")
        
        # Usa il coordinatore A2A
        response = coordinator.process_query(question)
        
        logger.info("Risposta ricevuta dal sistema A2A")
        
        # Restituisci la pagina con la risposta
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "city": city,
                "response": response,
                "error": None
            }
        )
        
    except Exception as e:
        logger.error(f"Errore: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "city": city if 'city' in locals() else "",
                "response": None,
                "error": f"Errore: {str(e)}"
            }
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

