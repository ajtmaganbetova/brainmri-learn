import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

uri = os.environ["MONGO_URI_CLOUD"]

subprocess.run(
    ["mongorestore", f"--uri={uri}", "--nsInclude=brainmri_learn.*", "./mongo_backup"],
    check=True,
)
