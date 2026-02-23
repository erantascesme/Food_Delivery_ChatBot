import json
import os
import time
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

# Setup API Key
os.environ["GOOGLE_API_KEY"] = "ADD-YOUR-API-KEY"

# Get base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_json(filename):
    # Use absolute path
    path = os.path.join(BASE_DIR, 'data', filename)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filename} not found in {path}")
        return []


def create_vector_db():
    # 1. Load the Catalog Data
    restaurants = load_json('restaurants.json')
    dishes = load_json('dishes.json')

    if not restaurants or not dishes:
        print("Error: Missing catalog data (restaurants or dishes).")
        return

    documents = []
    print(f"Indexing Data: {len(restaurants)} Restaurants, {len(dishes)} Dishes...")

    # 2. Create Searchable Documents
    for r in restaurants:
        food_types_str = ", ".join(r.get('food_types', []))
        rush_hours_str = ", ".join(r.get('rush_hours', []))
        hours_str = ", ".join([f"{k}: {v}" for k, v in r.get('hours', {}).items()])

        for dish_id in r.get('menu_dish_ids', []):
            dish = next((d for d in dishes if d['id'] == dish_id), None)
            if dish:
                ingredients_str = ", ".join(dish.get('ingredients', []))
                tags_str = ", ".join(dish.get('tags', []))
                prep_time = dish.get('preparation_time', '15')
                dish_rating = dish.get('rating', 'N/A')

                content = (
                    f"Dish Name: {dish['name']}\n"
                    f"Restaurant: {r['name']}\n"
                    f"Cuisine/Type: {food_types_str}\n"
                    f"Price: ${dish['price']}\n"
                    f"Dish Rating: {dish_rating}/5\n"
                    f"Preparation Time: {prep_time} minutes\n"
                    f"Ingredients: {ingredients_str}\n"
                    f"Tags/Flavor Profile: {tags_str}\n"
                    f"Restaurant Rating: {r.get('general_ranking', 'N/A')} stars\n"
                    f"Opening Hours: {hours_str}\n"
                    f"Rush Hours (Busy): {rush_hours_str}\n"
                    f"Active: {r.get('is_active', True)}"
                )

                metadata = {
                    "id": dish['id'],
                    "type": "dish",
                    "restaurant_id": r['id'],
                    "restaurant_name": r['name'],
                    "price": dish['price'],
                    "prep_time": prep_time,
                    "ranking": r.get('general_ranking', 0),
                    "dish_rating": dish_rating
                }

                documents.append(Document(page_content=content, metadata=metadata))

    # 3. Vectorize and Save (Batched to avoid Rate Limit)
    if documents:
        print(f"Vectorizing {len(documents)} rich documents...")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

        db = None
        # REDUCED BATCH SIZE TO 10
        batch_size = 10

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            print(f"Processing batch {i + 1}-{i + len(batch)}/{len(documents)}...")

            try:
                if db is None:
                    db = FAISS.from_documents(batch, embeddings)
                else:
                    db.add_documents(batch)
            except Exception as e:
                print(f"Error on batch {i}: {e}")
                # Simple retry logic if it fails
                print("Waiting 60s and retrying once...")
                time.sleep(60)
                if db is None:
                    db = FAISS.from_documents(batch, embeddings)
                else:
                    db.add_documents(batch)

            # Sleep between batches to respect API limits (100 req/min)
            if i + batch_size < len(documents):
                print("Sleeping 40s to respect API rate limits...")
                time.sleep(40)

        # SAVE TO ABSOLUTE PATH
        output_path = os.path.join(BASE_DIR, "faiss_index")
        if db:
            db.save_local(output_path)
            print(f"Success! All data indexed to '{output_path}'.")
        else:
            print("Error: Database creation failed.")
    else:
        print("No documents generated.")


if __name__ == "__main__":
    create_vector_db()