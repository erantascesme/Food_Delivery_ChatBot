# Conversational AI Recommender System & Trust Analysis

This repository contains the software and analytical tools developed for a research study exploring human-AI interaction, specifically focusing on user trust, explainability, and decision-making in Conversational Recommender Systems (CRS).

The project is divided into two main components: a fully functional simulated food delivery AI and a statistical analysis suite for evaluating user feedback.

## Repository Structure

### 1. `ChatBot APP`

This folder contains the core web application: an intelligent, conversational food-delivery assistant. Built with **Flask**, **LangChain**, and **Google Gemini**, the system acts as a personalized AI waiter.

* **RAG Architecture:** Uses a FAISS vector database to semantically match natural language queries with a simulated dataset of restaurants and dishes.
* **Dynamic Profiling:** Automatically updates user constraints (e.g., allergies, budget, spice tolerance) in real-time based on the conversation.
* **Explainability:** The LLM is explicitly prompted to justify its recommendations, providing transparent reasoning for why specific dishes were chosen based on the user's active constraints.

### 2. `Survey Results`

This folder contains the data analysis pipeline used to evaluate the human-AI interaction study. It includes scripts to perform statistical analysis on the surveys filled out by participants after interacting with the chatbot. The analysis measures key behavioral economics metrics, such as user trust, satisfaction, and the impact of the AI's explainability on their final choices.

---

## Application Previews

Here is a look at the Chatbot interface in action:


![Chat](https://github.com/user-attachments/assets/d3afe04c-9b25-4ac7-bdd4-33a3e7475db4)


**1. Main Chat Interface & User Profiling**

**2. Context-Aware Dish Recommendations**

**3. Detailed Explanations & Ordering Flow**

---

*Developed for academic research in Human-AI Interaction and Behavioral Economics.*
