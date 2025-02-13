from pyngrok import ngrok, conf
from app import create_app
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Token de autenticação do Ngrok
ngrok_auth_token = os.getenv('NGROK_AUTH_TOKEN')

# Configurar o ngrok
conf.get_default().auth_token = ngrok_auth_token
conf.get_default().region = 'us'  # ou sua região preferida

# Criar e configurar a aplicação Flask
app = create_app()

def start_ngrok():
    try:
        # Fechar túneis existentes
        ngrok.kill()
        
        # Configurar e iniciar novo túnel
        tunnel = ngrok.connect(5000, bind_tls=True)
        public_url = tunnel.public_url
        
        print("\n=== CONFIGURAÇÃO DO WEBHOOK ===")
        print(f"URL pública do ngrok: {public_url}")
        print(f"URL do webhook: {public_url}/stripe/webhook")
        print("\nConfigure esta URL no dashboard do Stripe:")
        print("1. Vá para https://dashboard.stripe.com/test/webhooks")
        print("2. Clique em 'Add endpoint'")
        print("3. Cole a URL do webhook acima")
        print("4. Selecione o evento 'checkout.session.completed'")
        print("\nAguardando eventos do Stripe...\n")
        
        return public_url
    except Exception as e:
        print(f"Erro ao iniciar ngrok: {e}")
        return None

if __name__ == '__main__':
    # Verificar versão do ngrok
    try:
        ngrok_version = ngrok.get_ngrok_version()
        print(f"Versão do ngrok: {ngrok_version}")
    except:
        print("Não foi possível determinar a versão do ngrok")

    # Iniciar o túnel ngrok
    public_url = start_ngrok()
    
    if public_url:
        # Iniciar o servidor Flask
        app.run(port=5000, debug=True)
    else:
        print("Erro ao iniciar o ngrok. Verifique sua instalação e token.")