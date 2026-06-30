# DBMST (Davnor Blue Marlins Swim Team)

A modern, data-driven platform for coaches and swimmers, featuring a premium glassmorphism UI, interactive charts, and Supabase integration.

## Local Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key
   SECRET_KEY=your_secure_flask_session_key
   ```

4. **Database Setup:**
   Copy the contents of `database_schema.sql` and run it in your Supabase project's SQL Editor to create all necessary tables, enums, and Row Level Security (RLS) policies.

5. **Run the Application:**
   ```bash
   python run.py
   ```
   Visit `http://localhost:5000` in your browser.

## Deployment

### Vercel (Recommended)
This repository contains a `vercel.json` file configured to deploy the Flask application as Vercel Serverless Functions.
1. Push this code to GitHub.
2. Import the repository in Vercel.
3. Add the environment variables in the Vercel Dashboard.
4. Deploy!

### Render / Railway (Alternative)
If your application scales beyond Vercel's serverless execution limits, you can easily deploy it as a standard web service using Gunicorn.
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn run:app`
