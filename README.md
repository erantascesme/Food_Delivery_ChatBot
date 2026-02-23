# Food-Delivery LLM Chatbot: A Human-AI Interaction Study

Food-delivery platforms often overwhelm users with choices, leading to cognitive fatigue and decision overload. While conversational Large Language Models (LLMs) offer a promising solution through personalized, natural-language recommendations, the inherent opacity of AI introduces a critical Human-AI Interaction challenge: user trust.

This repository contains the software and analytical tools developed for a research study exploring how Explainable AI (XAI) principles can bridge this gap. Specifically, the project investigates how transparent, preference-aligned explanations in Conversational Recommender Systems (CRS) help users anticipate system behavior, calibrate their trust, and ultimately influence their intention to adopt the technology.

The project is divided into two main components: a fully functional simulated food delivery AI and a statistical analysis suite for evaluating user feedback.

## Repository Structure

### 1. `ChatBot APP`

This folder contains the core web application: an intelligent, conversational food-delivery assistant. Built with **Flask**, **LangChain**, and **Google Gemini**, the system acts as a personalized AI waiter.

* **RAG Architecture:** Uses a FAISS vector database to semantically match natural language queries with a simulated dataset of restaurants and dishes.
* **Dynamic Profiling:** Automatically updates user constraints (e.g., allergies, budget, spice tolerance) in real-time based on the conversation.
* **Explainability:** The LLM is explicitly prompted to justify its recommendations, providing transparent reasoning for why specific dishes were chosen based on the user's active constraints.

### 2. `Survey Results`

This folder contains the data analysis pipeline used to evaluate the human-AI interaction study ($N=26$). The suite includes scripts to perform statistical analyses - such as internal consistency reliability (Cronbach's $\alpha$) and Ordinary Least Squares (OLS) regression on user survey data collected post-interaction. The code evaluates three primary research questions: how perceived explanation quality predicts experienced trust, how trust drives future usage intention, and whether baseline user characteristics moderate these effects. Additionally, it analyzes specific eXplainable AI (XAI) indicators, such as predictability and safety. The resulting statistical models demonstrate that transparent, high-quality explanations are a core mechanism for building user trust, which in turn strongly predicts a user's willingness to adopt the conversational recommender system.

---

## Application Previews

Here is a look at the Chatbot interface in action:


<img src="https://github.com/user-attachments/assets/d3afe04c-9b25-4ac7-bdd4-33a3e7475db4" alt="Main Chat Interface" width="600">

<img src="https://github.com/user-attachments/assets/a057c273-eebb-4cd9-b7e4-b467ef98a0c6" alt="Ordering Flow" height="300" width="300">


---

## Creators
* **Hadar Engel**, Tel Aviv University, https://www.linkedin.com/in/hadar-engel/
* **Eran Tascesme**, Tel Aviv University, https://www.linkedin.com/in/erantascesme/


*Developed for academic research in Human-AI Interaction and Behavioral Economics.*
