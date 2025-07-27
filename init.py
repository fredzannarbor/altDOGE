import subprocess
import sys
import os
import platform
import sqlite3
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AltDOGEInitializer:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.db_path = self.project_dir / "xtuff_collections.db"
        self.env_path = self.project_dir / ".env"
        self.requirements_path = self.project_dir / "requirements.txt"
        self.python_version = "3.12.3"
        self.src_dir = self.project_dir / "src"
        self.pages_dir = self.project_dir / "pages"

    def create_repository_structure(self) -> bool:
        """Create the repository structure with necessary directories and files."""
        try:
            # Create directories
            self.src_dir.mkdir(exist_ok=True)
            self.pages_dir.mkdir(exist_ok=True)

            # Create __init__.py in src
            (self.src_dir / "__init__.py").touch(exist_ok=True)

            # Create placeholder Streamlit page files
            page_files = [
                "1_dashboard.py",
                "2_analysis.py",
                "3_proposals.py",
                "4_comments.py",
                "5_settings.py"
            ]
            for page in page_files:
                page_path = self.pages_dir / page
                if not page_path.exists():
                    page_path.write_text(
                        """import streamlit as st
from src.database import Database
from src.authmanager import AuthManager

def main():
    db = Database("xtuff_collections.db")
    auth_manager = AuthManager(db)
    
    if not st.session_state.get("user_id"):
        st.error("Please log in to access this page.")
        st.stop()
    
    st.title(f"AltDOGE - {st.session_state.page_title}")
    st.write("Page under construction.")

if __name__ == "__main__":
    main()
"""
                    )

            # Create src files (minimal versions to ensure structure)
            src_files = {
                "app.py": """from dotenv import load_dotenv
import streamlit as st
from src.database import Database
from src.authmanager import AuthManager

load_dotenv()

def main():
    st.set_page_config(page_title="AltDOGE", layout="wide")
    db = Database("xtuff_collections.db")
    auth_manager = AuthManager(db)
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    
    if not st.session_state.user_id:
        st.title("AltDOGE - Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                user_id = auth_manager.authenticate(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        st.title("AltDOGE - Regulatory Reform Platform")
        st.write("Use the sidebar to navigate.")

if __name__ == "__main__":
    main()
""",
                "database.py": """import sqlite3
from typing import Any, List, Tuple
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: Tuple = ()) -> List[Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()
""",
                "authmanager.py": """from src.database import Database
from typing import Optional
import hashlib

class AuthManager:
    def __init__(self, db: Database):
        self.db = db

    def authenticate(self, username: str, password: str) -> Optional[int]:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        query = "SELECT id FROM users WHERE username = ? AND password_hash = ?"
        result = self.db.execute_query(query, (username, password_hash))
        return result[0][0] if result else None
""",
                "litellm_fallback.py": """import litellm
from typing import Dict, Any
import backoff
import os

class LiteLLMFallback:
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def completion_with_fallback(self, prompt: str) -> Dict[str, Any]:
        try:
            response = litellm.completion(
                model=os.getenv("LITELLM_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}]
            )
            return {"status": "success", "response": response.choices[0].message.content}
        except Exception as e:
            print(f"LLM error, attempting fallback: {str(e)}")
            try:
                response = litellm.completion(
                    model="claude-3.7-sonnet",
                    messages=[{"role": "user", "content": prompt}]
                )
                return {"status": "success", "response": response.choices[0].message.content}
            except Exception as fallback_e:
                print(f"Fallback failed: {str(fallback_e)}")
                return {"status": "error", "message": str(fallback_e)}
""",
                "stripe_integration.py": """import stripe
from src.database import Database
from typing import Dict, Any
import os

class StripeIntegration:
    def __init__(self, db: Database):
        stripe.api_key = os.getenv("STRIPE_API_KEY")
        self.db = db

    def create_subscription(self, user_id: int, price_id: str) -> Dict[str, Any]:
        try:
            customer = stripe.Customer.create(
                metadata={"user_id": user_id}
            )
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price_id}]
            )
            return {"status": "success", "subscription_id": subscription.id}
        except stripe.error.StripeError as e:
            print(f"Stripe error: {str(e)}")
            return {"status": "error", "message": str(e)}
""",
                "webhook_handler.py": """import stripe
import streamlit as st
from src.database import Database
import os

class WebhookHandler:
    def __init__(self, db: Database):
        self.db = db
        self.endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.endpoint_secret
            )
            if event["type"] == "customer.subscription.created":
                pass  # Update database
            return {"status": "success"}
        except ValueError as e:
            print(f"Webhook error: {str(e)}")
            return {"status": "error", "message": str(e)}
"""
            }
            for file_name, content in src_files.items():
                file_path = self.src_dir / file_name
                if not file_path.exists():
                    file_path.write_text(content)

            # Create LICENSE
            license_path = self.project_dir / "LICENSE"
            if not license_path.exists():
                license_path.write_text(
                    """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION
...
[Full Apache 2.0 License text]
"""
                )

            # Create .gitignore
            gitignore_path = self.project_dir / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text(
                    """# Python
__pycache__/
*.py[cod]
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
ENV/

# Database
xtuff_collections.db

# Environment
.env
uv.lock

# Logs
*.log

# IDE
.idea/
.vscode/

# OS generated files
.DS_Store
Thumbs.db
"""
                )

            logger.info("Repository structure created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating repository structure: {str(e)}")
            return False

    def check_python_version(self) -> bool:
        """Check if the correct Python version is installed."""
        try:
            current_version = platform.python_version()
            if current_version != self.python_version:
                logger.warning(f"Python {self.python_version} required, found {current_version}")
                return self.install_python()
            logger.info(f"Python {current_version} is correct")
            return True
        except Exception as e:
            logger.error(f"Error checking Python version: {str(e)}")
            return False

    def install_python(self) -> bool:
        """Install Python 3.12.3 using system package manager."""
        try:
            if sys.platform.startswith("linux"):
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", f"python{self.python_version}"], check=True)
            elif sys.platform == "darwin":
                subprocess.run(["brew", "install", f"python@{self.python_version}"], check=True)
            else:
                logger.error("Unsupported platform for automatic Python installation")
                return False
            logger.info(f"Python {self.python_version} installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Python: {str(e)}")
            return False

    def install_uv(self) -> bool:
        """Install uv package manager."""
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "uv==0.4.24"], check=True)
            logger.info("uv installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error installing uv: {str(e)}")
            return False

    def install_dependencies(self) -> bool:
        """Install dependencies using uv."""
        try:
            requirements_content = """\
streamlit==1.46.0
stripe==10.12.0
litellm==1.48.0
python-dotenv==1.0.1
pandas==2.2.3
numpy==2.1.2
requests==2.32.3
"""
            self.requirements_path.write_text(requirements_content)
            subprocess.run(["uv", "pip", "install", "-r", str(self.requirements_path)], check=True)
            logger.info("Dependencies installed successfully with uv")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Error installing dependencies: {str(e)}")
            return False

    def init_database(self) -> bool:
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS regulations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        reg_number TEXT NOT NULL,
                        title TEXT,
                        text TEXT,
                        effective_date TEXT,
                        agency TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        stripe_subscription_id TEXT,
                        status TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """)
                conn.commit()
            logger.info("Database initialized successfully")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {str(e)}")
            return False

    def create_env_file(self) -> bool:
        """Create .env file with default configuration, prompting for sensitive keys."""
        try:
            if self.env_path.exists():
                logger.info(".env file already exists, skipping creation")
                return True

            stripe_api_key = input("Enter Stripe API Key (or press Enter to skip): ").strip() or "your_stripe_api_key"
            stripe_webhook_secret = input("Enter Stripe Webhook Secret (or press Enter to skip): ").strip() or "your_stripe_webhook_secret"
            litellm_api_key = input("Enter LLM API Key (or press Enter to skip): ").strip() or "your_llm_api_key"
            federal_register_api_key = input("Enter Federal Register API Key (optional, press Enter to skip): ").strip() or "your_federal_register_api_key"

            env_content = f"""\
STRIPE_API_KEY={stripe_api_key}
STRIPE_WEBHOOK_SECRET={stripe_webhook_secret}
LITELLM_MODEL=gpt-4o
LITELLM_API_KEY={litellm_api_key}
FEDERAL_REGISTER_API_KEY={federal_register_api_key}
"""
            self.env_path.write_text(env_content)
            logger.info(".env file created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating .env file: {str(e)}")
            return False

    def write_python_version(self) -> bool:
        """Write .python-version file for pyenv compatibility."""
        try:
            (self.project_dir / ".python-version").write_text(self.python_version)
            logger.info(".python-version file created")
            return True
        except Exception as e:
            logger.error(f"Error writing .python-version: {str(e)}")
            return False

    def init_git(self) -> bool:
        """Initialize Git repository and make initial commit."""
        try:
            git_dir = self.project_dir / ".git"
            if not git_dir.exists():
                subprocess.run(["git", "init"], cwd=self.project_dir, check=True)
                subprocess.run(["git", "add", "."], cwd=self.project_dir, check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit for AltDOGE"], cwd=self.project_dir, check=True)
                logger.info("Git repository initialized and initial commit made")
            else:
                logger.info("Git repository already initialized")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error initializing Git: {str(e)}")
            return False

    def run(self) -> bool:
        """Run the initialization process."""
        logger.info("Starting AltDOGE initialization...")
        
        steps = [
            (self.create_repository_structure, "Creating repository structure"),
            (self.check_python_version, "Checking Python version"),
            (self.install_uv, "Installing uv package manager"),
            (self.install_dependencies, "Installing dependencies"),
            (self.init_database, "Initializing database"),
            (self.create_env_file, "Creating .env file"),
            (self.write_python_version, "Writing .python-version file"),
            (self.init_git, "Initializing Git repository")
        ]

        for step_func, step_name in steps:
            logger.info(f"Executing: {step_name}")
            if not step_func():
                logger.error(f"Initialization failed at step: {step_name}")
                return False

        logger.info("AltDOGE initialization completed successfully")
        logger.info("Run the application with: python run_altdoge.py")
        return True

if __name__ == "__main__":
    initializer = AltDOGEInitializer()
    success = initializer.run()
    sys.exit(0 if success else 1)