from pathlib import Path

import joblib
import pandas as pd

# Resolved relative to this file (not the process cwd) so it loads correctly
# regardless of where uvicorn is started from.
MODEL_PATH = Path(__file__).parent / "model" / "medidiag_model.pkl"
MODEL = joblib.load(MODEL_PATH)

# CRITICAL: this list is pulled directly from the trained model's own
# feature_names_in_, not hand-typed, and MUST stay this way. See project
# history for why: a previous hand-typed list caused every prediction to
# silently receive symptoms in the wrong input slots.
SYMPTOMS = list(MODEL.feature_names_in_)


def run_diagnosis(selected_symptoms):
    row = {s: (1 if s in selected_symptoms else 0) for s in SYMPTOMS}
    input_df = pd.DataFrame([row], columns=SYMPTOMS)

    prediction = str(MODEL.predict(input_df)[0])
    probabilities = MODEL.predict_proba(input_df)[0]

    # predict_proba returns numpy.float64 -- round() on those is still a
    # numpy.float64, which psycopg2/Postgres can't adapt (it silently stringifies
    # to "np.float64(...)" and gets embedded raw in the SQL, breaking every insert).
    # SQLite tolerated it; Postgres doesn't, so cast to native float explicitly.
    malaria_pct = round(float(probabilities[MODEL.classes_.tolist().index("Malaria")]) * 100, 2)
    typhoid_pct = round(float(probabilities[MODEL.classes_.tolist().index("Typhoid")]) * 100, 2)

    drug = "Artemisinin Combination Therapy (ACT)" if prediction == "Malaria" else "Ciprofloxacin"

    return prediction, drug, malaria_pct, typhoid_pct
