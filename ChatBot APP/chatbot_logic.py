import os
import json
import math
import datetime
import re
import random
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from typing import Any
from pydantic import BaseModel


# ---------------------------------------------------------
# PATCH 1: Fix Pydantic V1/V2 compatibility on AWS
# ---------------------------------------------------------
def patched_setstate(self, state: Any) -> None:
    if isinstance(state, dict):
        for old_key, new_key in [
            ("__fields_set__", "__pydantic_fields_set__"),
            ("__private_attributes__", "__pydantic_private__"),
        ]:
            if old_key in state and new_key not in state:
                state[new_key] = state.pop(old_key)
        state.setdefault("__pydantic_extra__", None)
        state.setdefault("__pydantic_private__", None)
    self.__dict__.update(state)


BaseModel.__setstate__ = patched_setstate


# ---------------------------------------------------------
# PATCH 2: Simple Document Wrapper
# ---------------------------------------------------------
class SimpleDocument:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


# --- SETUP CHAINS ---
try:
    from langchain.chains import create_history_aware_retriever, create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
except (ImportError, ModuleNotFoundError):
    from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
    from langchain_classic.chains.retrieval import create_retrieval_chain
    from langchain_classic.chains.combine_documents import create_stuff_documents_chain

# API Key Setup
os.environ["GOOGLE_API_KEY"] = "ADD-YOUR-API-KEY"


class FoodDeliveryChatbot:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(self.base_dir, "faiss_index")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

        if not os.path.exists(index_path):
            raise RuntimeError(f"Index not found at {index_path}. Did you run ingest.py? Is it in .ebignore?")

        self.vector_db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            temperature=0.3
        )

        profiles_dir = os.path.join(self.base_dir, 'data', 'profiles')
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir, exist_ok=True)

        self.reload_data()
        self.active_orders = {}

    def reload_data(self):
        data_dir = os.path.join(self.base_dir, 'data')
        try:
            with open(os.path.join(data_dir, 'customers.json'), 'r') as f:
                self.customers = {c['id']: c for c in json.load(f)}
            with open(os.path.join(data_dir, 'restaurants.json'), 'r') as f:
                self.restaurants = {r['id']: r for r in json.load(f)}
            with open(os.path.join(data_dir, 'deliverers.json'), 'r') as f:
                self.deliverers = json.load(f)

            # Ensure keys are strings for robust lookup
            with open(os.path.join(data_dir, 'dishes.json'), 'r') as f:
                self.dishes = {str(d['id']): d for d in json.load(f)}

            orders_path = os.path.join(data_dir, 'orders.json')
            if os.path.exists(orders_path):
                with open(orders_path, 'r') as f:
                    self.orders = json.load(f)
            else:
                self.orders = []
        except Exception as e:
            print(f"Data Load Error: {e}")
            self.customers = {}

    def get_customer(self, user_id):
        return self.customers.get(user_id)

    def _calc_dist(self, lat1, lon1, lat2, lon2):
        return math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2)

    def get_full_profile_json(self, user_id):
        c = self.customers.get(user_id)
        if not c: return "{}"
        if 'preferences' not in c: c['preferences'] = {}

        defaults = {
            "diet": [], "allergies": [], "intolerances": [], "religious_restrictions": [],
            "hated_ingredients": [], "texture_aversions": [], "spice_level": "medium",
            "preferred_flavors": [], "avoid_flavors": [], "nutrition_goals": [],
            "favorite_cuisines": [], "avoid_cuisines": [], "preferred_dish_types": [],
            "preferred_proteins": [], "avoid_proteins": [], "occasion": "",
            "time_limit_minutes": None, "budget": {"min": None, "max": None, "currency": "$"},
            "customization_preference": "some", "portion_preference": "",
            "adventurousness": "medium", "character_summary": "New customer."
        }
        current_prefs = c.get('preferences', {})
        for k, v in defaults.items():
            if k not in current_prefs: current_prefs[k] = v
        return json.dumps(current_prefs, indent=2)

    def update_profile_db(self, user_id, new_prefs):
        if user_id not in self.customers:
            self.reload_data()

        customer = self.customers.get(user_id)
        if not customer: return

        current_prefs = customer.get('preferences', {})
        if isinstance(new_prefs, dict):
            current_prefs.update(new_prefs)

        customer['preferences'] = current_prefs
        self.customers[user_id] = customer

        try:
            with open(os.path.join(self.base_dir, 'data', 'customers.json'), 'w') as f:
                json.dump(list(self.customers.values()), f, indent=4)
            with open(os.path.join(self.base_dir, 'data', 'profiles', f"{user_id}_constraints.json"), 'w') as f:
                json.dump(new_prefs, f, indent=4)
        except Exception as e:
            print(f"Error saving profile: {e}")

    def get_formatted_sidebar_data(self, user_id):
        user = self.customers.get(user_id)
        if not user:
            self.reload_data()
            user = self.customers.get(user_id)

        if not user: return "No Data", "No Data"

        prof = user.get('preferences', {})
        summary_text = prof.get('character_summary', 'New customer.')

        lines = []
        for key, label in [
            ('diet', '🥗 Diet'), ('allergies', '🚫 Allergies'), ('intolerances', '⚠️ Intolerance'),
            ('religious_restrictions', '🙏 Religious'), ('hated_ingredients', '👎 Hates'),
            ('texture_aversions', '🤢 Texture'), ('avoid_flavors', '😝 Avoid Flavors'),
            ('nutrition_goals', '💪 Goals'), ('favorite_cuisines', '❤️ Cuisines')
        ]:
            if prof.get(key):
                val = prof[key]
                if isinstance(val, list):
                    val = ", ".join([str(x).strip() for x in val])
                lines.append(f"{label}: {val}")

        if prof.get('budget', {}).get('max'):
            lines.append(f"💰 Budget: <= {prof['budget']['max']} $")

        return "\n".join(lines) if lines else "No specific restrictions.", summary_text

    def finalize_order(self, user_id, rating, chat_history):
        order_info = self.active_orders.pop(user_id, None)
        if not order_info: return {"msg": "Error", "reset": False}

        dish_id = order_info['dish_id']
        dish_name = order_info['dish_name']
        restaurant_id = "Unknown"
        for r in self.restaurants.values():
            if dish_id in r.get('menu_dish_ids', []): restaurant_id = r['id']; break

        summary_text = f"Ordered {dish_name} (Rated {rating}/5)."

        new_order = {
            "id": f"O{len(self.orders) + 101}", "customer_id": user_id, "restaurant_id": restaurant_id,
            "ordered_dishes_ids": [dish_id], "ranking": int(rating),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "conversation_summary": summary_text
        }
        self.orders.append(new_order)
        try:
            with open(os.path.join(self.base_dir, 'data', 'orders.json'), 'w') as f:
                json.dump(self.orders, f, indent=4)
        except:
            pass

        return {"msg": f"Order confirmed! Starting new session...", "reset": True, "summary": summary_text}

    def chat(self, user_input, chat_history, user_id):
        if user_id not in self.customers:
            self.reload_data()

        if user_id in self.active_orders and user_input.strip().isdigit():
            res = self.finalize_order(user_id, int(user_input.strip()), chat_history)
            c, s = self.get_formatted_sidebar_data(user_id)
            return {"bot_response": res['msg'], "reset_chat": res['reset'], "last_summary": res['summary'],
                    "constraints": c, "user_summary": s, "recommendations": []}

        if user_input.startswith("CMD:PLACE_ORDER"):
            try:
                parts = user_input.split("|")
                self.active_orders[user_id] = {"dish_id": parts[1], "dish_name": parts[2]}
                c, s = self.get_formatted_sidebar_data(user_id)
                return {
                    "bot_response": f"Ordering {parts[2]}.<br><strong>Tap star rating to confirm.</strong>",
                    "constraints": c, "user_summary": s, "recommendations": []
                }
            except:
                pass

        clean_docs = []
        try:
            raw_docs = self.vector_db.similarity_search(user_input, k=20)
            for doc in raw_docs:
                if hasattr(doc, '__dict__'):
                    content = doc.__dict__.get('page_content', '')
                    meta = doc.__dict__.get('metadata', {})
                else:
                    content = getattr(doc, 'page_content', "")
                    meta = getattr(doc, 'metadata', {})

                rest_id = meta.get('restaurant_id')
                dish_id = meta.get('id')

                if rest_id:
                    rest = self.restaurants.get(rest_id)
                    if rest and rest.get('is_active', True):
                        enriched_content = f"Dish ID: {dish_id}\n{content}"
                        clean_docs.append(SimpleDocument(page_content=enriched_content, metadata=meta))
        except Exception as e:
            print(f"Vector DB Retrieval Error: {e}")

        # --- FALLBACK MECHANISM ---
        # If vector search failed or returned nothing, grab 20 random dishes to ensure context exists.
        if not clean_docs:
            print("Warning: Empty context from Vector DB. Using random fallback dishes.")
            all_dishes = list(self.dishes.values())
            random_dishes = random.sample(all_dishes, min(len(all_dishes), 20))
            for d in random_dishes:
                # Basic string reconstruction
                ing_str = ", ".join(d.get('ingredients', []))
                content = f"Dish Name: {d['name']}\nPrice: ${d['price']}\nIngredients: {ing_str}"
                enriched_content = f"Dish ID: {d['id']}\n{content}"
                clean_docs.append(SimpleDocument(page_content=enriched_content, metadata={'id': d['id']}))

        user_obj = self.customers.get(user_id, {})
        old_prefs = user_obj.get('preferences', {}).copy()

        current_profile_json = self.get_full_profile_json(user_id)

        system_prompt = """
        You are an advanced Food Delivery AI Assistant powered by Gemini 3.

        ### PART 1: PREFERABLES MANAGER (Profile Update)
        Input: "{input}"
        Current Profile: {current_profile_json}

        **Task:** Update the JSON profile with specific constraints.
        1. **Religious/Ethical:** Kosher, Halal, etc -> "religious_restrictions".
        2. **Intolerances:** Lactose, Gluten -> "intolerances".
        3. **Sensory:** "I hate mushy food" -> "texture_aversions".
        4. **Flavors:** "I love sour stuff" -> "preferred_flavors".
        5. **Cuisines:** "I want Asian" -> "favorite_cuisines".
        6. **Budget:** "Under 50 shekels" -> update "budget.max".
        7. **Summary:** Update 'character_summary' with their personality.

        ### PART 2: RECOMMENDATION ENGINE
        1. Analyze the Context provided below (list of available dishes).
        2. Filter by ALL profile constraints (Religion, Intolerances, Diet).
        3. **MANDATORY:** You MUST select exactly 3 dishes from the Context.
           - If user constraints eliminate all options, you MUST relax the least critical constraint (e.g., flavor preference) to find 3 valid options.
           - Explicitly explain why you picked them (e.g., "This matches your diet but is slightly over budget").
           - Do NOT say "I don't have a list". The list is in the Context.

        Context: {context}

        ### OUTPUT JSON
        {{
            "bot_response": "...",
            "updated_profile": {{ ... (The FULL updated profile object) ... }},
            "recommendations": [
                {{ "name": "...", "id": "...", "restaurant": "...", "price": 0, "eta": "...", "explanation": "..." }}
            ]
        }}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])

        chain = create_stuff_documents_chain(self.llm, prompt)

        parsed = {}
        try:
            result = chain.invoke({
                "input": user_input,
                "chat_history": chat_history,
                "context": clean_docs,
                "current_profile_json": current_profile_json
            })

            clean_json = result.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"\{.*\}", clean_json, re.DOTALL)
            parsed = json.loads(json_match.group(0)) if json_match else {}
        except Exception as e:
            print(f"LLM Error: {e}")
            parsed = {"updated_profile": json.loads(current_profile_json), "recommendations": []}

        sys_msg = "Ready"
        if "updated_profile" in parsed:
            new_prefs = parsed["updated_profile"]

            changes = []
            for k, v in new_prefs.items():
                old_v = old_prefs.get(k)
                if isinstance(v, list) and isinstance(old_v, list):
                    if set(v) != set(old_v): changes.append(k)
                elif v != old_v:
                    changes.append(k)

            self.update_profile_db(user_id, new_prefs)

            if changes:
                formatted_changes = [c.replace('_', ' ').title() for c in changes]
                visible_changes = [c for c in formatted_changes if c not in ['Character Summary']]
                if visible_changes:
                    sys_msg = f"📝 Updated: {', '.join(visible_changes)}"
                else:
                    sys_msg = "📝 Profile Refined"
            else:
                sys_msg = "Ready"

        recommendations = parsed.get("recommendations", [])
        valid_recommendations = []

        for rec in recommendations:
            # SMART INGREDIENT & RATING LOOKUP
            raw_id = str(rec.get('id', '')).strip()
            nums = re.findall(r'\d+', raw_id)
            num_part = nums[0] if nums else ""

            possible_ids = [raw_id]
            if num_part:
                possible_ids.append(f"D{num_part.zfill(3)}")
                possible_ids.append(f"D{num_part}")
                possible_ids.append(num_part)

            dish_obj = None
            for pid in possible_ids:
                if pid in self.dishes:
                    dish_obj = self.dishes[pid]
                    break

            # Fallback search by Name if ID failed
            if not dish_obj:
                target_name = rec.get('name', '').lower().strip()
                for d in self.dishes.values():
                    db_name = d.get('name', '').lower().strip()
                    if db_name == target_name or (len(target_name) > 4 and target_name in db_name):
                        dish_obj = d
                        break

            # STRICT FILTER: Only return dishes that exist in our DB
            if dish_obj:
                ing = dish_obj.get('ingredients', [])
                rec['ingredients'] = ", ".join(ing) if ing else "Ingredients unavailable."
                rec['rating'] = dish_obj.get('rating', 'N/A')
                valid_recommendations.append(rec)
            else:
                # Skip hallucinated dishes that don't match any known ID or Name
                continue

        c_html, s_html = self.get_formatted_sidebar_data(user_id)

        return {
            "bot_response": parsed.get("bot_response", "Here are some options:"),
            "constraints": c_html,
            "user_summary": s_html,
            "system_msg": sys_msg,
            "recommendations": valid_recommendations
        }