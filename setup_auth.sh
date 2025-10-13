#!/bin/bash
# Script per configurare l'autenticazione gcloud

echo "🔐 Configurazione autenticazione Google Cloud..."

# Aggiungi gcloud al PATH
export PATH="/opt/homebrew/bin:$PATH"

# Verifica se gcloud è installato
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI non trovato. Installazione..."
    brew install google-cloud-sdk
fi

echo "🔑 Login con Google Cloud..."
gcloud auth login

echo "🔧 Configurazione Application Default Credentials..."
gcloud auth application-default login

echo "✅ Autenticazione configurata!"
echo ""
echo "Ora puoi usare il client Gemini senza API key:"
echo "  poetry run python src/client/gemini_working_client.py"
