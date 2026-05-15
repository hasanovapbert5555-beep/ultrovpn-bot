import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
SERVER_HOST = os.getenv("SERVER_HOST", "5.129.218.41")
DB_PATH = "ultrovpn.db"
LOG_LEVEL = "INFO"
EOF
