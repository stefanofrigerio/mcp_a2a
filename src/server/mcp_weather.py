from typing import Any, Sequence
import httpx
import logging
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configura logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    logger.info("📋 Lista tool richiesta")
    tools = [
        Tool(
            name="get_alerts",
            description="Get weather alerts for a US state",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Two-letter US state code (e.g. CA, NY)"
                    }
                },
                "required": ["state"]
            }
        ),
        Tool(
            name="get_forecast",
            description="Get weather forecast for a location",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the location"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the location"
                    }
                },
                "required": ["latitude", "longitude"]
            }
        )
    ]
    logger.info(f"✅ Restituiti {len(tools)} tool")
    return tools

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    logger.info(f"Chiamata tool: {name} con argomenti: {arguments}")
    
    if name == "get_alerts":
        state = arguments.get("state")
        if not state:
            return [TextContent(type="text", text="Errore: stato richiesto")]
        
        try:
            logger.info(f"Chiamata get_alerts per stato: {state}")
            url = f"{NWS_API_BASE}/alerts/active/area/{state}"
            logger.debug(f"URL richiesta: {url}")
            
            data = await make_nws_request(url)
            logger.debug(f"Dati ricevuti: {data is not None}")

            if not data or "features" not in data:
                logger.warning("Nessun dato o features non trovato")
                return [TextContent(type="text", text="Unable to fetch alerts or no alerts found.")]

            if not data["features"]:
                logger.info("Nessun alert attivo")
                return [TextContent(type="text", text="No active alerts for this state.")]

            alerts = [format_alert(feature) for feature in data["features"]]
            result = "\n---\n".join(alerts)
            logger.info(f"Restituiti {len(alerts)} alerts")
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.error(f"Errore in get_alerts: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    elif name == "get_forecast":
        latitude = arguments.get("latitude")
        longitude = arguments.get("longitude")
        
        if latitude is None or longitude is None:
            return [TextContent(type="text", text="Errore: latitudine e longitudine richieste")]
        
        try:
            logger.info(f"Chiamata get_forecast per lat: {latitude}, lon: {longitude}")
            
            # First get the forecast grid endpoint
            points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
            logger.debug(f"URL punti: {points_url}")
            points_data = await make_nws_request(points_url)

            if not points_data:
                logger.error("Impossibile ottenere dati punti")
                return [TextContent(type="text", text="Unable to fetch forecast data for this location.")]

            # Get the forecast URL from the points response
            forecast_url = points_data["properties"]["forecast"]
            logger.debug(f"URL previsioni: {forecast_url}")
            forecast_data = await make_nws_request(forecast_url)

            if not forecast_data:
                logger.error("Impossibile ottenere previsioni dettagliate")
                return [TextContent(type="text", text="Unable to fetch detailed forecast.")]

            # Format the periods into a readable forecast
            periods = forecast_data["properties"]["periods"]
            logger.info(f"Trovati {len(periods)} periodi")
            forecasts = []
            for period in periods[:5]:  # Only show next 5 periods
                forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
                forecasts.append(forecast)

            result = "\n---\n".join(forecasts)
            logger.info("Previsioni formattate e restituite")
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.error(f"Errore in get_forecast: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Tool sconosciuto: {name}")]

async def main():
    """Main function to run the server."""
    logger.info("🌤️ Avvio Weather MCP Server...")
    logger.info("📡 Creazione stdio server...")
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("✅ Stdio server creato")
            logger.info("🔧 Creazione opzioni di inizializzazione...")
            init_options = server.create_initialization_options()
            logger.info("✅ Opzioni create")
            logger.info("🚀 Avvio server.run...")
            await server.run(
                read_stream,
                write_stream,
                init_options
            )
            logger.info("✅ Server.run completato")
    except Exception as e:
        logger.error(f"❌ Errore in main: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Errore nel server: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)