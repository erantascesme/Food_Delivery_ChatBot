import json
import os
import random
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, abort
from langchain_core.messages import HumanMessage, AIMessage
from chatbot_logic import FoodDeliveryChatbot

application = Flask(__name__)

app = application
app.secret_key = 'super_duper_sumos2'

# Initialize Bot
bot = None

def get_bot():
    global bot
    if bot is None:
        try:
            bot = FoodDeliveryChatbot()
        except Exception as e:
            abort(503, description=f"Chatbot failed to initialize: {e}")
    return bot


bot = get_bot()
user_histories = {}


# --- HELPER FUNCTIONS ---
def load_customers():
    try:
        with open('data/customers.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_customers(customers):
    with open('data/customers.json', 'w') as f:
        json.dump(customers, f, indent=4)


# --- ROUTES ---
@app.route('/', methods=['GET'])
def index():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login_page'))


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        return render_template('login.html')
    return login()


@app.route('/process_login', methods=['POST'])
def login():
    identifier = request.form.get('user_id')

    # 1. Try finding by ID directly
    customer = bot.get_customer(identifier)

    # 2. If not found, search by Name (Case insensitive)
    if not customer:
        for c_id, c_data in bot.customers.items():
            if c_data.get('name', '').lower() == identifier.lower().strip():
                customer = c_data
                identifier = c_id 
                break

    if customer:
        session['user_id'] = identifier
        session['user_name'] = customer['name']
        return redirect(url_for('chat'))
    else:
        return render_template('login.html', error="User not found")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    if request.method == 'POST':
        customers = load_customers()
        new_id = f"C{len(customers) + 1:03d}"

        # Extract Data
        name = request.form.get('name')
        city = request.form.get('city')
        street = request.form.get('street')
        house = request.form.get('house_number')
        phone = request.form.get('phone_number')

        # Create Profile with Defaults
        # We fetch the default structure from the bot logic to ensure consistency
        default_prefs = json.loads(bot.get_full_profile_json(None))

        new_customer = {
            "id": new_id,
            "name": name,
            "city": city,
            "street": street,
            "house_number": house,
            "phone_number": phone,
            "latitude": 40.75 + (random.uniform(-0.02, 0.02)),
            "longitude": -73.98 + (random.uniform(-0.02, 0.02)),
            "previous_orders_ids": [],
            "profile": {},
            "preferences": default_prefs
        }

        customers.append(new_customer)
        save_customers(customers)
        bot.reload_data()

        session['user_id'] = new_id
        session['user_name'] = name

        # Store new ID in session to show popup in chat
        session['new_user_id'] = new_id

        return redirect(url_for('chat'))


@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session.get('user_id')
    bot.reload_data()
    constraints_text, summary_text = bot.get_formatted_sidebar_data(user_id)

    # Check for new user flag for popup
    new_user_id = session.pop('new_user_id', None)

    return render_template('chat.html',
                           user_name=session.get('user_name'),
                           user_id=user_id,
                           initial_constraints=constraints_text,
                           initial_summary=summary_text,
                           new_user_id=new_user_id)


@app.route('/api/message', methods=['POST'])
def handle_message():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_input = data.get('message')
    user_id = session['user_id']
    history = user_histories.get(user_id, [])

    response_data = bot.chat(user_input, history, user_id)

    history.append(HumanMessage(content=user_input))
    history.append(AIMessage(content=response_data['bot_response']))
    user_histories[user_id] = history

    return jsonify(response_data)


# --- NEW ROUTE: GET RAW PROFILE FOR EDITING ---
@app.route('/api/get_profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session: return jsonify({}), 401
    user_id = session['user_id']

    # Use helper to get full structure (including empty fields)
    profile_json = bot.get_full_profile_json(user_id)
    return jsonify(json.loads(profile_json))


# --- NEW ROUTE: SAVE EDITED PROFILE ---
@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session: return jsonify({}), 401
    user_id = session['user_id']
    new_prefs = request.json

    # Save using existing logic
    bot.update_profile_db(user_id, new_prefs)

    # Get updated formatted strings for UI
    bot.reload_data()
    constraints, summary = bot.get_formatted_sidebar_data(user_id)

    return jsonify({
        "status": "success",
        "constraints": constraints,
        "user_summary": summary
    })


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)