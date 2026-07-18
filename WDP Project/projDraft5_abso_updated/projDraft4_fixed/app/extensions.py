from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Flask extensions are created here and initialised in run.py.

db = SQLAlchemy()
migrate = Migrate()
