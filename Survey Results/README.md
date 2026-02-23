# Survey Results & Statistical Analysis

This directory contains the dataset and the analytical pipeline used to evaluate the human-AI interaction study. The analysis measures how the conversational recommender system's explainability affects user trust and adoption intentions.

## 📂 Directory Contents

* **`Answers.csv`**
The raw, anonymized survey data collected from participants. This includes initial responses covering demographics, prior app usage, baseline trust in AI, and raw Likert-scale responses regarding their post-interaction experience with the chatbot.
* **`Answers_with_scores_and_xai.csv`**
The cleaned and processed dataset used for the final statistical modeling (). This file includes aggregated composite scores derived from the raw data, such as:
* **BaselineTrust:** The user's inherent propensity to trust AI.
* **ExplanationQuality:** How clear and useful the AI's justifications were perceived to be.
* **TrustTotal:** The overall post-interaction experienced trust (aggregating Benevolence, Competence, and Reciprocity).
* **UsageIntention:** The user's willingness to adopt the chatbot.
* **XAI Indicators:** Specific explainable AI trust metrics including Predictability, Safety, and Calibration.


* **`survey_stats.ipynb`**
A Jupyter Notebook containing the complete statistical analysis pipeline. The notebook is structured to directly answer the study's Research Questions (RQ1, RQ2, and RQ3) and includes:
* **Data Screening & Descriptives:** Internal consistency reliability checks (Cronbach’s ) and descriptive statistics.
* **Regression Modeling:** Ordinary Least Squares (OLS) regression models (with HC3 robust standard errors) testing the relationships between explanation quality, trust, and usage intention.
* **Moderation Analysis:** Interaction models testing whether baseline traits moderate the formation of trust.
* **Visualizations:** The code used to generate the scatter plots, partial residual plots, and standardized coefficient charts presented in the final paper.



## 🛠️ Requirements to Run

To execute the `survey_stats.ipynb` notebook locally, you will need a standard Python data science environment. Recommended libraries include:

* `pandas` (for data manipulation)
* `numpy` (for numerical operations)
* `statsmodels` (for OLS regression and robust standard errors)
* `matplotlib` & `seaborn` (for generating figures)
