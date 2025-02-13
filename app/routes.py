from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, current_app, session
from firebase_admin import auth, firestore
from anthropic import Anthropic
import stripe
from functools import wraps  # Adicionando esta importação
import os
import json
import logging
from datetime import datetime
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
        # Verificação da API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("Anthropic API key not found in environment variables")
            return "Error: Anthropic API key not configured. Please contact support."
        
        if not api_key.startswith('sk-ant-'):
            logger.error("Invalid Anthropic API key format")
            return "Error: Invalid API key format. Please check your configuration."
        
        # Criar a mensagem usando a API da Anthropic
        response = anthropic.messages.create(
            model="claude-3-opus-20240229",
            messages=[{
                "role": "user",
                "content": user_input
            }],
            max_tokens=max_tokens
        )
        
        logger.info(f"AI request processed successfully for user: {session.get('user_email')}")
        return response.content[0].text
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Anthropic API error: {str(e)}")
        
        if "rate_limit" in error_msg.lower():
            return "Too many requests. Please try again in a few seconds."
        elif "invalid_api_key" in error_msg.lower():
            return "API configuration error. Please contact support."
        else:
            return f"Error processing your request: {error_msg}"
        
@main.route('/ai-services', methods=['GET', 'POST'])
def ai_services():
    if request.method == 'POST':
        try:
            data = request.get_json()
            user_input = data.get('input', '')
            
            if not user_input:
                return jsonify({'error': 'Input vazio'}), 400

            response = call_ai_api(user_input)
            
            return jsonify({
                'response': response,
                'status': 'success'
            })

        except Exception as e:
            logger.error(f"Erro no endpoint ai-services: {str(e)}")
            return jsonify({
                'error': 'Erro ao processar requisição',
                'message': str(e)
            }), 500
    
    return render_template('ai_service.html')

@main.route('/check-api-key')
def check_api_key():
    api_key = os.getenv('ANTHROPIC_API_KEY')
    return {
        'key_exists': bool(api_key),
        'key_length': len(api_key) if api_key else 0,
        'key_start': api_key[:10] + '...' if api_key else 'None',
        'key_format_correct': api_key.startswith('sk-ant-') if api_key else False
    }

@main.route('/api/ai-generate', methods=['POST'])
@require_active_subscription
def api_ai_generate():
    try:
        data = request.get_json()
        user_input = data.get('prompt')
        
        if not user_input:
            return jsonify({'error': 'No prompt provided'}), 400
            
        response = call_ai_api(user_input)
        
        return jsonify({
            'status': 'success',
            'response': response
        })
        
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500




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
                
                # Dados do cliente e da compra
                customer_data = {
                    'name': customer_details.get('name'),
                    'email': customer_details.get('email'),
                    'phone': customer_details.get('phone'),
                    'address': customer_details.get('address', {}),
                    'stripe_customer_id': session.get('customer'),
                    'subscription_status': 'active',
                    'current_plan': session.get('metadata', {}).get('plan_name'),
                    'last_payment': {
                        'date': datetime.utcnow().isoformat(),
                        'amount': session.get('amount_total'),
                        'currency': session.get('currency'),
                        'payment_method': session.get('payment_method_types', ['card'])[0],
                        'status': session.get('payment_status'),
                        'session_id': session.get('id')
                    }
                }

                print("Dados do cliente atualizados:")
                print(json.dumps(customer_data, indent=4))

                # Atualizar ou criar documento do cliente
                customers_ref = db.collection('customers').document(customer_details.get('email'))
                customers_ref.set(customer_data, merge=True)

                # Registrar histórico de pagamento
                payment_history = {
                    'session_id': session.get('id'),
                    'date': datetime.utcnow().isoformat(),
                    'plan_name': session.get('metadata', {}).get('plan_name'),
                    'amount': session.get('amount_total'),
                    'currency': session.get('currency'),
                    'payment_method': session.get('payment_method_types', ['card'])[0],
                    'status': session.get('payment_status')
                }

                print("Novo registro de pagamento:")
                print(json.dumps(payment_history, indent=4))

                db.collection('payment_history').document(session.get('id')).set(payment_history)

                # Atualizar status do usuário se existir
                users_ref = db.collection('users')
                query = users_ref.where('email', '==', customer_details.get('email'))
                user_docs = query.get()
                
                for user_doc in user_docs:
                    user_doc.reference.update({
                        'subscription_status': 'active',
                        'current_plan': session.get('metadata', {}).get('plan_name'),
                        'last_payment': payment_history
                    })
                    print(f"Status do usuário atualizado: {customer_details.get('email')}")

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
                # Atualizar documento do usuário
                user.reference.update({
                    'subscription_status': 'active',
                    'last_payment_date': datetime.utcnow().isoformat()
                })
                
                # Atualizar sessão
                session['subscription_status'] = 'active'
                print(f"Subscription status updated for user: {customer_email}")  # Debug log
                
                flash('Subscription activated successfully!', 'success')
                return redirect(url_for('main.ai_services'))

        except Exception as e:
            print(f"Error in success route: {str(e)}")  # Debug log
            flash('Error processing payment confirmation.', 'error')
            
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

@main.route('/test-firebase')
def test_firebase():
    try:
        # Testar Firestore
        db = firestore.client()
        test_ref = db.collection('_test').document('connection')
        test_ref.set({
            'timestamp': datetime.utcnow().isoformat(),
            'test': True
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Firebase connection successful',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'type': type(e).__name__
        }), 500