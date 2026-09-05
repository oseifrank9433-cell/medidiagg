# MediDiag — Malaria & Typhoid Fever Screening Suite

A React front-end for a clinician-facing hospital app: sign up / log in, run a
structured symptom review for a patient, and see a side-by-side likelihood
comparison between malaria and typhoid fever, plus a patient record list.

## Getting started

```bash
npm install
npm run dev
```

Open the printed local URL (usually http://localhost:5173).

To build for production:

```bash
npm run build
npm run preview   # serve the production build locally
```

## What's included

- **Login / Signup** — split-screen branded auth screens with real hero
  photography, and a light/dark mode toggle (also in the sidebar once
  signed in).
- **Two account types** — pick "Clinician" or "Administrator" at signup.
  Clinicians land on the screening dashboard; administrators land on a
  separate facility-wide admin console. Clinicians can't see the admin
  console, and vice versa — each role is redirected away from the other's
  routes automatically.
- **Clinician Dashboard** — welcome banner, quick stats (total screenings,
  malaria/typhoid split, urgent flags, average fever duration, most
  reported symptom), a 14-day trends chart, an age/sex breakdown chart, and
  a recent-activity table.
- **Admin Dashboard** — the same kind of overview aggregated across every
  clinician account on the device, plus a per-clinician screening count
  table and CSV/PDF export of facility-wide records.
- **New Screening** — a 4-step form: patient details → vitals → symptom
  checklist → review, then runs the screening.
- **Patient Records** — search by name, filter by urgency and date range,
  and export the filtered list to CSV or PDF. Each record has a detail
  view with the full likelihood breakdown and reported symptoms.
- **Profile page** — clinicians and admins can update their name, email,
  facility, title, and password.

## How the screening works

`src/utils/diagnosisEngine.js` holds a weighted symptom checklist. Each
symptom has a malaria weight and a typhoid weight based on commonly taught
clinical differentiators (fever pattern, GI symptoms, joint pain, rash,
etc.), plus a small adjustment from temperature and fever duration. It
outputs a percentage split between the two conditions and an urgency flag.

**This is a screening / triage aid only.** It is rule-based, not a trained
diagnostic model, and is not a substitute for confirmatory lab testing
(RDT or blood film for malaria; Widal test, blood or stool culture for
typhoid). The in-app disclaimer on the result page reflects this — keep it
if you present this to your supervisor or in production.

## Data & accounts

This frontend talks to a real backend (`medidiag_api/`, FastAPI +
SQLAlchemy). Accounts, patient records, and facility settings are stored
server-side; passwords are hashed with bcrypt and sessions use JWTs.

There's no seeded admin login — sign up once with "Administrator" selected
and the correct admin PIN (set via `MEDIDIAG_ADMIN_PIN` on the backend) to
create one. The PIN is checked server-side, not in the browser.

Set `VITE_API_URL` (see `.env.example`) to point this frontend at your
running backend. See `medidiag_api/README`-equivalent notes and
`.env.example` there for the backend's own required environment variables
(`MEDIDIAG_SECRET_KEY`, `MEDIDIAG_ADMIN_PIN`, `CORS_ORIGINS`, and optionally
`DATABASE_URL` for Postgres in production).

## Stack

- React 19 + Vite
- react-router-dom for routing
- Plain CSS with a design-token system (`src/index.css` + `src/styles/app.css`)
  — no UI framework, so every color/spacing choice is easy to find and tune.

## Customizing the look

All colors, fonts, and radii live as CSS variables at the top of
`src/index.css`. Change them there and the whole app updates.
