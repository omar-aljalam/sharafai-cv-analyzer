# CV Analyzer API

FastAPI backend application for processing and analyzing CVs/Resumes, built with PostgreSQL, SQLAlchemy, Alembic, and Docker.

---

## Getting Started

Follow these steps to get your local development environment up and running.

### 1. Clone the Repository
```bash
git clone https://github.com/omar-aljalam/sharafai-cv-analyzer.git
cd cv-analyzer
```

### 2. Set Up Environment Variables
```bash
cp .env.example .env
```
---

## Running with Docker (Recommended)

The easiest way to run the entire stack (FastAPI app + PostgreSQL database + automatic migrations).

### Start the application:
```bash
docker compose up --build
```
* **Why --build?** You must use this flag the first time you clone the repo, or whenever changes are made to environment recipes. These changes include updating requirements.txt, modifying the Dockerfile, or editing docker-compose.yml. It guarantees Docker updates your application container image to match the code changes.
* **Active URLs:** Once running, the API documentation is available at **http://localhost:8080/docs**. Press `Ctrl + C` in the terminal to stop the application safely.

---

## Local Python Environment & Package Management

If you need to write new code, install external libraries, or run code formatters inside VS Code, set up a local virtual environment.

### 1. Create and Activate the `.venv`
```bash
# Create the environment
python -m venv .venv

# Activate on Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate on Mac/Linux
source .venv/bin/activate
```
* **Why?** Creating a `.venv` sandboxes this project's packages. It prevents your system-wide global Python installation from conflicting with the dependencies required by this project.

### 2. Install Existing Dependencies
```bash
pip install -r requirements.txt
```
* **Why?** This syncs your newly created local workspace environment with the exact package versions (like FastAPI, Pydantic, and SQLAlchemy) specified by the project.

### 3. Adding New Packages & Freezing
```bash
pip install <package_name>
pip freeze > requirements.txt
```
* **Why `pip freeze`?** If you install a package, it only exists on your local machine. Running `pip freeze > requirements.txt` records the package name and version to a shared file. 
* **Next Step:** Once committed to Git, your teammates will receive it, and Docker will build it on their next container startup.

---

## Database Migrations (Alembic)

Whenever you make changes or additions to your database tables inside `app/models.py`, you must generate a new migration tracking script so the database updates its structure.

You can generate this script using  directly inside the running Docker container.

### Using Docker
```bash
docker compose exec web alembic revision --autogenerate -m "describe your schema changes here"
```
---

### Verify Your Configuration State
To ensure your environment file is properly linked and communicating with the database without making structural alterations, run:
```bash
docker compose exec web alembic current

```
* **Why?** This acts as a safe connectivity test. It checks if your environment successfully reads your root `.env` file, hooks into the active database, and displays your current database schema state without modifying anything.
* **Note on Deploying Migrations:** Our `entrypoint.sh` container startup script automatically runs `alembic upgrade head` every time the Docker stack boots up. However, if Docker is **already running** when you generate a new migration, it will not apply live automatically. You must apply it manually by running:
```bash
  docker compose exec web alembic upgrade head
  # or
  docker compose restart web
```

---

##  Git Workflow & Pull Request (PR) Policy

To maintain a stable code base, **direct commits or merges to the `main` branch are strictly prohibited**. Follow this exact feature-branch workflow for all task assignments:

### 1. Sync Your Main Branch
Before starting any new task, ensure your local repository has the latest updates from the team:
```bash
git checkout main
git pull origin main
```

### 2. Create a Dedicated Feature Branch
Never work directly inside the `main` branch. Create a descriptive branch named after your task:
```bash
git checkout -b feature/your-feature-name
# Examples: feature/user-auth, feature/cv-parser, bugfix/db-connection
```

### 3. Commit and Push Your Work
Keep your commit messages descriptive and structured:
```bash
git add .
git commit -m "user registration endpoint and password hashing"
git push origin feature/your-feature-name
```

### 4. Open a Pull Request (PR)
Once your feature is complete and working locally:
1. Go to the repository github.
2. Click **New Pull Request**.
3. Set `main` as the **base** branch, and your `feature/your-feature-name` as the **compare** branch.
4. Fill out the PR description template clearly explaining what you changed and why.

### 5. Code Review & Merge Constraints
* **No Self-Merging:** You cannot merge your own PR into `main`.
* **Peer Approvals:** At least **one team member** must review, test, and approve your code logic before it can be merged.