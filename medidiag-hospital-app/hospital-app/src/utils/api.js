import { DEFAULT_CONFIDENCE_THRESHOLD } from './diagnosisEngine';
import { API_BASE_URL } from './apiClient';

/**
 * Fetches the canonical, backend-defined symptom list (the model's fixed
 * feature set). Mostly useful for debugging/verifying the frontend and
 * backend symptom ids stay in sync.
 */
export async function getSymptoms() {
  const res = await fetch(`${API_BASE_URL}/symptoms`);
  if (!res.ok) {
    throw new Error('Failed to load symptom list from server.');
  }
  const data = await res.json();
  return data.symptoms;
}

/**
 * Sends selected symptom ids to the backend and returns a diagnosis.
 * The backend always returns its raw model prediction — the confidence
 * threshold (below which we defer to "Unknown / Refer to Clinician") is
 * applied here, client-side, so it can be facility-configurable without
 * requiring backend changes per facility.
 *
 * @param {string[]} selectedSymptoms - array of symptom ids, e.g. ["high_fever", "chills"]
 * @param {number} [confidenceThreshold] - 0-100, defaults to DEFAULT_CONFIDENCE_THRESHOLD
 */
export async function getDiagnosis(selectedSymptoms, confidenceThreshold = DEFAULT_CONFIDENCE_THRESHOLD) {
  const res = await fetch(`${API_BASE_URL}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symptoms: selectedSymptoms }),
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || 'Diagnosis request failed.');
  }

  const data = await res.json();
  const malariaPct = data.malaria_pct;
  const typhoidPct = data.typhoid_pct;

  const topPct = Math.max(malariaPct, typhoidPct);
  if (topPct < confidenceThreshold) {
    return {
      diagnosis: 'Unknown / Refer to Clinician',
      drug: 'No automatic prescription. Recommend laboratory testing.',
      malariaPct,
      typhoidPct,
    };
  }

  return {
    diagnosis: data.diagnosis,
    drug: data.drug,
    malariaPct,
    typhoidPct,
  };
}
