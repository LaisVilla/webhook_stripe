from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, current_app, session
from firebase_admin import auth, firestore
from anthropic import Anthropic
import stripe
from functools import wraps  # Adicionando esta importação
import os
import json
import logging
from datetime import datetime
import pytz
# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

# Configuração do Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Configuração do Anthropic
anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def require_active_subscription(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please login to access this feature.', 'error')
            return redirect(url_for('main.login'))
        
        try:
            # Verificar status atual no Firestore
            db = firestore.client()
            user_doc = db.collection('users').document(session['user_id']).get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                current_status = user_data.get('subscription_status', 'inactive')
                
                # Atualizar sessão com status atual
                session['subscription_status'] = current_status
                
                if current_status != 'active':
                    flash('You need an active subscription to access this feature.', 'warning')
                    return redirect(url_for('main.payments'))
            else:
                flash('User not found. Please login again.', 'error')
                return redirect(url_for('main.login'))
                
        except Exception as e:
            print(f"Error checking subscription: {str(e)}")  # Debug log
            flash('Error verifying subscription status.', 'error')
            return redirect(url_for('main.payments'))
            
        return f(*args, **kwargs)
    return decorated_function


@main.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.get_json()
        logger.info(f"Dados recebidos: {json.dumps(data, indent=4)}")
        return jsonify({'status': 'success', 'data': data}), 200
    return render_template('index.html')

# Atualizar a rota de login para incluir a imagem do perfil na sessão
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Log inicial da tentativa de login
        print(f"\n=== Login Attempt ===")
        print(f"Email: {email}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return redirect(url_for('main.login'))
        
        try:
            # Buscar usuário diretamente no Firestore primeiro
            db = firestore.client()
            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1).get()
            
            user_found = False
            for user_doc in query:
                user_found = True
                user_data = user_doc.to_dict()
                
                try:
                    # Verificar credenciais no Firebase Auth
                    user = auth.get_user_by_email(email)
                    
                    # Se chegou aqui, o usuário existe no Firebase Auth
                    print(f"User found in Firebase Auth: {user.uid}")
                    
                    # Configurar sessão
                    session['user_id'] = user.uid
                    session['user_email'] = email
                    session['user_name'] = user_data.get('name')
                    session['profile_image'] = user_data.get('profile_image_url')
                    session['subscription_status'] = user_data.get('subscription_status', 'inactive')
                    
                    # Atualizar último login
                    user_doc.reference.update({
                        'last_login': datetime.utcnow().isoformat(),
                    })
                    
                    print("Session data updated successfully")
                    print(f"Session: {session}")
                    
                    flash('Login successful!', 'success')
                    
                    # Redirecionar baseado no status da assinatura
                    if user_data.get('subscription_status') == 'active':
                        return redirect(url_for('main.ai_services'))
                    else:
                        return redirect(url_for('main.payments'))
                
                except auth.UserNotFoundError:
                    print(f"User not found in Firebase Auth: {email}")
                    flash('Invalid email or password.', 'error')
                    return redirect(url_for('main.login'))
                
                except Exception as auth_error:
                    print(f"Firebase Auth error: {str(auth_error)}")
                    flash('Authentication error. Please try again.', 'error')
                    return redirect(url_for('main.login'))
            
            if not user_found:
                print(f"User not found in Firestore: {email}")
                flash('Invalid email or password.', 'error')
                return redirect(url_for('main.login'))
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            return redirect(url_for('main.login'))
    
    return render_template('login.html')
    

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone = request.form.get('phone')
        
        print(f"\n=== Registration Attempt ===")
        print(f"Email: {email}")
        print(f"Name: {name}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        
        try:
            # Verificar se o usuário já existe
            db = firestore.client()
            existing_users = db.collection('users').where('email', '==', email).get()
            
            if len(list(existing_users)) > 0:
                flash('Email already registered.', 'error')
                return redirect(url_for('main.register'))
            
            # Criar usuário no Firebase Auth
            user = auth.create_user(
                email=email,
                password=password
            )
            
            # Criar cliente no Stripe
            stripe_customer = stripe.Customer.create(
                email=email,
                name=name,
                phone=phone
            )
            
            # Criar documento do usuário
            user_data = {
                'email': email,
                'name': name,
                'phone': phone,
                'stripe_customer_id': stripe_customer.id,
                'created_at': datetime.utcnow().isoformat(),
                'last_login': datetime.utcnow().isoformat(),
                'subscription_status': 'inactive',
                'payment_history': [],
                'current_plan': None,
                'profile_image_url': None
            }
            
            # Salvar no Firestore usando o UID do Firebase Auth
            db.collection('users').document(user.uid).set(user_data)
            
            print(f"\n=== User Created Successfully ===")
            print(f"UID: {user.uid}")
            print(f"Email: {email}")
            
            # Configurar sessão
            session['user_id'] = user.uid
            session['user_email'] = email
            session['user_name'] = name
            session['subscription_status'] = 'inactive'
            
            flash('Account created successfully!', 'success')
            return redirect(url_for('main.payments'))
            
        except auth.EmailAlreadyExistsError:
            print(f"Email already exists: {email}")
            flash('Error: Email already registered.', 'error')
            return redirect(url_for('main.register'))
            
        except Exception as e:
            print(f"Registration error: {str(e)}")
            flash('Error creating account. Please try again.', 'error')
            return redirect(url_for('main.register'))
    
    return render_template('register.html')

# Função para chamar a API da OpenAI
def call_ai_api(user_input, max_tokens=150):
    try:
        # Registro de data/hora UTC e usuário
        current_utc = datetime.now(pytz.UTC)
        formatted_date = current_utc.strftime('%Y-%m-%d %H:%M:%S')
        user_login = session.get('user_email', 'Unknown')
        
        logger.info(f"""
        ============================
        Nova Requisição AI
        Timestamp (UTC): {formatted_date}
        Usuário: {user_login}
        Input: {user_input}
        ============================
        """)

        # Buscar usuário no Firestore
        db = firestore.client()
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', user_login).limit(1)
        user_docs = query.get()

        if not user_docs:
            logger.error(f"Usuário não encontrado para atualização de estatísticas - Email: {user_login}")
            return "Erro: Usuário não encontrado"

        user_doc = user_docs[0]
        user_dict = user_doc.to_dict()
        
        # Verificar estatísticas antes da chamada
        ai_stats = user_dict.get('ai_stats', {
            'total_requests': 0,
            'remaining_requests': 10,
            'total_tokens': 0,
            'last_reset': formatted_date
        })
            # Verificar se ainda tem requisições disponíveis
        if ai_stats['remaining_requests'] <= 0:
            logger.warning(f"Limite de requisições atingido - Usuário: {user_login}")
            return "Você atingiu o limite de requisições para este mês. Aguarde o próximo mês para mais requisições."

        # Verificação da API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        logger.debug(f"API Key presente: {'Sim' if api_key else 'Não'}")
        
        if not api_key:
            logger.error(f"API key não encontrada - Usuário: {user_login} - UTC: {formatted_date}")
            return "Error: Anthropic API key not configured. Please contact support."
        
        if not api_key.startswith('sk-ant-'):
            logger.error(f"Formato inválido da API key - Usuário: {user_login} - UTC: {formatted_date}")
            return "Error: Invalid API key format. Please check your configuration."
        
        # Inicializar cliente Anthropic com a chave
        logger.debug("Inicializando cliente Anthropic")
        client = Anthropic(api_key=api_key)
        
        # Criar a mensagem usando a API da Anthropic
        logger.debug("Enviando requisição para Anthropic API")
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=[{
                "role": "user",
                "content": user_input
            }],
            max_tokens=max_tokens
        )
        
        # Log da resposta
        logger.debug(f"Resposta recebida da API: {response.content}")
        
        if not response.content:
            logger.error("Resposta vazia da API")
            return "Erro: Resposta vazia da API"
        
        # Após resposta bem-sucedida, atualizar estatísticas
        if response.content:
            # Verificar reset mensal
            last_reset = datetime.strptime(ai_stats['last_reset'], '%Y-%m-%d %H:%M:%S')
            if last_reset.month != current_utc.month:
                ai_stats['remaining_requests'] = 1000
                ai_stats['last_reset'] = formatted_date
            
            # Atualizar contadores
            ai_stats['total_requests'] += 1
            ai_stats['remaining_requests'] = max(0, ai_stats['remaining_requests'] - 1)
            ai_stats['total_tokens'] += len(user_input.split())
            
            # Atualizar documento
            user_doc.reference.update({'ai_stats': ai_stats})
            
            return response.content[0].text
        
    except Exception as e:
        error_msg = str(e)
        current_utc = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
        user_login = session.get('user_email', 'Unknown')
        
        logger.error(f"""
        ============================
        Erro na API Anthropic
        Timestamp (UTC): {current_utc}
        Usuário: {user_login}
        Erro: {error_msg}
        Stack Trace: {logging.traceback.format_exc()}
        ============================
        """)
        
        if "401" in error_msg or "authentication_error" in error_msg:
            return "Erro de autenticação com a API. Por favor, contate o suporte técnico."
        elif "rate_limit" in error_msg.lower():
            return "Muitas requisições. Por favor, tente novamente em alguns segundos."
        else:
            return f"Erro ao processar sua requisição: {error_msg}"
def update_user_ai_stats(user_login, tokens_used):
    try:
        current_utc = datetime.now(pytz.UTC)
        formatted_date = current_utc.strftime('%Y-%m-%d %H:%M:%S')
         
         # Obter a instância do Firestore usando current_app
        db = firestore.client()

        # Buscar documento do usuário
        user_doc = db.collection('users').document(user_login)
        user_data = user_doc.get()
        
        if not user_data.exists:
            logger.error(f"Documento não encontrado ao atualizar estatísticas - Usuário: {user_login}")
            return
        
        # Obter ou criar estatísticas
        ai_stats = user_data.to_dict().get('ai_stats', {
            'total_requests': 0,
            'remaining_requests': 1000,
            'total_tokens': 0,
            'last_reset': formatted_date
        })
        
        # Atualizar estatísticas
        ai_stats['total_requests'] += 1
        ai_stats['remaining_requests'] = max(0, ai_stats['remaining_requests'] - 1)
        ai_stats['total_tokens'] += tokens_used
        
        # Salvar atualizações
        user_doc.update({
            'ai_stats': ai_stats
        })
        
        logger.info(f"Estatísticas atualizadas - Usuário: {user_login} - Tokens: {tokens_used}")
        
    except Exception as e:
        logger.error(f"""
        ============================
        Erro ao Atualizar Estatísticas
        Timestamp (UTC): {formatted_date}
        Usuário: {user_login}
        Erro: {str(e)}
        Stack Trace: {logging.traceback.format_exc()}
        ============================
        """)        

@main.route('/ai-services', methods=['GET', 'POST'])
def ai_services():
    print(f"[DEBUG] Método da requisição: {request.method}")
    
    if request.method == 'POST':
        try:
            print("[DEBUG] Processando POST request")
            print(f"[DEBUG] Headers: {dict(request.headers)}")
            print(f"[DEBUG] Dados brutos: {request.get_data(as_text=True)}")
            
            if not request.is_json:
                print("[DEBUG] Requisição não é JSON")
                return jsonify({
                    'error': 'Request must be JSON',
                    'message': 'Content-Type must be application/json'
                }), 400

            data = request.get_json()
            print(f"[DEBUG] Dados JSON: {data}")
            
            user_input = data.get('input', '').strip()
            print(f"[DEBUG] Input do usuário: {user_input}")
            
            # Chamar a API
            response = call_ai_api(user_input)
            print(f"[DEBUG] Resposta da API: {response}")
            
            return jsonify({
                'response': response,
                'status': 'success'
            })

        except Exception as e:
            print(f"[ERROR] Erro no processamento: {str(e)}")
            return jsonify({
                'error': 'Erro ao processar requisição',
                'message': str(e)
            }), 500

    return render_template('ai_services.html')

@main.route('/api/user/ai-stats', methods=['GET'])
def get_user_ai_stats():
    try:
        current_utc = datetime.now(pytz.UTC)
        formatted_date = current_utc.strftime('%Y-%m-%d %H:%M:%S')
        user_login = session.get('user_email')  # Pegamos o email
        user_name = session.get('user_name', 'Unknown')  # Pegamos o nome para log
        
        logger.info(f"""
        ============================
        Requisição de Estatísticas AI
        Timestamp (UTC): {formatted_date}
        Usuário: {user_name}
        Email: {user_login}
        ============================
        """)

        # Verificar autenticação
        if not user_login or user_login == 'Unknown':
            logger.error(f"Usuário não autenticado - UTC: {formatted_date}")
            return jsonify({
                'error': 'Usuário não autenticado',
                'timestamp': formatted_date
            }), 401
    
        # Fazer query para encontrar o usuário pelo email
        db = firestore.client()
        users_ref = db.collection('users')
        # Buscar usuário pelo email
        query = users_ref.where('email', '==', user_login).limit(1)
        user_docs = query.get()
        
        if not user_docs:
            logger.error(f"Usuário não encontrado - Email: {user_login} - UTC: {formatted_date}")
            return jsonify({
                'error': 'Usuário não encontrado',
                'timestamp': formatted_date,
            }), 404
        
        user_doc = user_docs[0]  # Pegar o primeiro documento encontrado
        user_dict = user_doc.to_dict()
        
        # Se não existir ai_stats, criar com valores iniciais
        if 'ai_stats' not in user_dict:
            ai_stats = {
                'total_requests': 0,
                'remaining_requests': 1000,
                'total_tokens': 0,
                'last_reset': formatted_date
            }
            user_doc.reference.update({'ai_stats': ai_stats})
        else:
            ai_stats = user_dict['ai_stats']
            
            # Verificar reset mensal
            last_reset = datetime.strptime(ai_stats['last_reset'], '%Y-%m-%d %H:%M:%S')
            if last_reset.month != current_utc.month:
                ai_stats.update({
                    'remaining_requests': 1000,
                    'last_reset': formatted_date
                })
                user_doc.reference.update({'ai_stats': ai_stats})

        usage_percentage = ((1000 - ai_stats['remaining_requests']) / 1000) * 100

        return jsonify({
            'status': 'success',
            'data': {
                'total_requests': ai_stats['total_requests'],
                'remaining_requests': ai_stats['remaining_requests'],
                'total_tokens': ai_stats['total_tokens'],
                'usage_percentage': usage_percentage,
                'timestamp': formatted_date,
                'user_name': user_dict.get('name', user_name),
                'subscription_status': user_dict.get('subscription_status', 'inactive')
            }
        })

    except Exception as e:
        error_msg = str(e)
        logger.error(f"""
        ============================
        Erro ao Buscar Estatísticas
        Timestamp (UTC): {formatted_date}
        Usuário: {user_name}
        Email: {user_login}
        Erro: {error_msg}
        Stack Trace: {logging.traceback.format_exc()}
        ============================
        """)
        
        return jsonify({
            'error': 'Erro ao buscar estatísticas',
            'message': error_msg,
            'timestamp': formatted_date
        }), 500

@main.route('/debug-user/<email>')
def debug_user(email):
    db = firestore.client()
    user_doc = db.collection('users').document(email).get()
    if user_doc.exists:
        return jsonify({
            'exists': True,
            'data': user_doc.to_dict()
        })
    return jsonify({
        'exists': False,
        'email_checked': email
    })

@main.route('/payments', methods=['GET', 'POST'])
def payments():
    if request.method == 'POST':
        plan_id = request.form.get('plan_id')
        email = request.form.get('email')
        name = request.form.get('name')
        phone = request.form.get('phone')
        
        plan = current_app.config['PLANS'].get(plan_id)
        
        if not plan:
            print(f"Plano inválido selecionado: {plan_id}")
            flash('Invalid plan selected.', 'danger')
            return redirect(url_for('main.payments'))

        try:
            # Criar sessão de checkout do Stripe
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': plan['name'],
                            'description': plan['description'],
                        },
                        'unit_amount': plan['price'],
                    },
                    'quantity': 1,
                }],
                mode='payment',
                customer_email=email,
                success_url=url_for('main.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('main.cancel', _external=True),
                metadata={
                    'plan_id': plan_id,
                    'plan_name': plan['name']
                }
            )

            session_data = {
                'created_at': datetime.utcnow().isoformat(),
                'customer_info': {
                    'email': email,
                    'name': name,
                    'phone': phone
                },
                'payment_info': {
                    'plan_id': plan_id,
                    'plan_name': plan['name'],
                    'amount': plan['price'],
                    'currency': 'usd',
                    'payment_method': 'card',
                    'payment_status': 'pending'
                }
            }

            # Salvar dados da sessão no Firestore
            db = firestore.client()
            db.collection('checkout_sessions').document(session.id).set(session_data)

            print("Nova sessão de checkout criada:")
            print(json.dumps(session_data, indent=4))

            return redirect(session.url, code=303)
        except Exception as e:
            print(f"Erro ao criar sessão de checkout: {str(e)}")
            flash(f'Error creating checkout session: {e}', 'danger')
            return redirect(url_for('main.payments'))

    plans = current_app.config['PLANS']
    return render_template('payments.html', plans=plans)

@main.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config['STRIPE_WEBHOOK_SECRET']

    try:
        event = stripe.Webhook.construct_event(
            payload=payload.encode(),
            sig_header=sig_header,
            secret=endpoint_secret
        )
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            customer_details = session.get('customer_details', {})
            
            try:
                db = firestore.client()
                
                # Preparar dados do pagamento
                payment_data = {
                    'session_id': session.get('id'),
                    'date': datetime.utcnow().isoformat(),
                    'plan_name': session.get('metadata', {}).get('plan_name'),
                    'amount': session.get('amount_total'),
                    'currency': session.get('currency'),
                    'payment_method': session.get('payment_method_types', ['card'])[0],
                    'status': session.get('payment_status')
                }

                # Buscar usuário pelo email
                users_ref = db.collection('users')
                query = users_ref.where('email', '==', customer_details.get('email'))
                user_docs = query.get()
                
                for user_doc in user_docs:
                    user_data = user_doc.to_dict()
                    
                    # Atualizar ou criar array de histórico de pagamentos
                    payment_history = user_data.get('payment_history', [])
                    payment_history.append(payment_data)
                    
                    # Preparar dados atualizados do usuário
                    update_data = {
                        'subscription_status': 'active',
                        'current_plan': session.get('metadata', {}).get('plan_name'),
                        'stripe_customer_id': session.get('customer'),
                        'payment_history': payment_history,
                        'last_payment': payment_data,
                        'subscription_updated_at': datetime.utcnow().isoformat(),
                        'customer_details': {
                            'name': customer_details.get('name'),
                            'email': customer_details.get('email'),
                            'phone': customer_details.get('phone'),
                            'address': customer_details.get('address', {})
                        }
                    }

                    # Atualizar documento do usuário
                    user_doc.reference.update(update_data)
                    
                    print(f"Usuário atualizado com sucesso: {customer_details.get('email')}")
                    print("Dados atualizados:", json.dumps(update_data, indent=2))

            except Exception as e:
                print(f"Erro ao atualizar banco de dados: {str(e)}")
                logger.error(f"Erro ao atualizar banco de dados: {str(e)}")
                return jsonify({'error': str(e)}), 500

    except ValueError as e:
        print(f"Payload inválido: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        print(f"Assinatura inválida: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        print(f"Erro no webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500

    return jsonify({'status': 'success'})

@main.route('/success')
def success():
    session_id = request.args.get('session_id')
    if session_id:
        try:
            stripe_session = stripe.checkout.Session.retrieve(session_id)
            customer_email = stripe_session.customer_details.email

            # Atualizar status no Firestore
            db = firestore.client()
            users_ref = db.collection('users')
            user_query = users_ref.where('email', '==', customer_email).limit(1).get()
            
            for user in user_query:
                user_data = user.to_dict()
                
                # Preparar dados do pagamento
                payment_data = {
                    'session_id': session_id,
                    'date': datetime.utcnow().isoformat(),
                    'plan_name': stripe_session.metadata.get('plan_name'),
                    'amount': stripe_session.amount_total,
                    'currency': stripe_session.currency,
                    'payment_method': 'card',
                    'status': stripe_session.payment_status
                }

                # Atualizar ou criar array de histórico de pagamentos
                payment_history = user_data.get('payment_history', [])
                payment_history.append(payment_data)

                # Atualizar documento do usuário
                update_data = {
                    'subscription_status': 'active',
                    'current_plan': stripe_session.metadata.get('plan_name'),
                    'payment_history': payment_history,
                    'last_payment': payment_data,
                    'subscription_updated_at': datetime.utcnow().isoformat()
                }
                
                user.reference.update(update_data)
                
                # Atualizar sessão
                session['subscription_status'] = 'active'
                print(f"Status da assinatura atualizado para o usuário: {customer_email}")
                
                flash('Assinatura ativada com sucesso!', 'success')
                return redirect(url_for('main.ai_services'))

        except Exception as e:
            print(f"Erro na rota success: {str(e)}")
            flash('Erro ao processar confirmação de pagamento.', 'error')
            
    return render_template('success.html')

@main.route('/cancel')
def cancel():
    return render_template('cancel.html')

# Suas outras rotas permanecem iguais
@main.route('/dashboard')
def dashboard():
    user_id = request.args.get('user_id')
    db = firestore.client()
    user_ref = db.collection('users').document(user_id).get()

    if user_ref.exists:
        user_data = user_ref.to_dict()
        print(f"Dados do usuário carregados:")
        print(json.dumps(user_data, indent=4))
        
        # Adicionar histórico de uso da IA
        ai_requests = db.collection('ai_requests')\
            .where('user_email', '==', user_data.get('email'))\
            .order_by('timestamp', direction='DESCENDING')\
            .limit(5)\
            .stream()
            
        ai_history = []
        for req in ai_requests:
            ai_history.append(req.to_dict())
            
        user_data['ai_history'] = ai_history
    else:
        user_data = None
        print(f"Usuário não encontrado: {user_id}")

    return render_template('dashboard.html', user_data=user_data)

@main.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('main.index'))
