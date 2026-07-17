(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned)

"python.terminal.activateEnvironment": true

(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& c:\Users\Administrator\Desktop\Centralized_Recipe_System\venv\Scripts\Activate.ps1)

LEGACY TABLES
DO NOT USE FOR NEW DEVELOPMENT

recipe_master
recipe_parameters
recipe_versions
recipe_version_values

$env:CRS_FLASK_DEBUG = "1"
$env:CRS_FLASK_RELOAD = "0"
python app.py