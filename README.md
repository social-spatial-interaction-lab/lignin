## First-time setup

Open Command Prompt (cmd) and navigate to the project root directory, then run the following commands in order:

```
python -m venv .venv
.\.venv\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
```

then Create an admin account for login:
```
python manage.py createsuperuser
```

Next, open the .env file in the project root and replace the value after
DEEPINFRA_API_TOKEN= with your actual API token.

Then start the development server:

```
python manage.py runserver
```
Finally, open http://localhost:8000/
in your browser to start using the application.


## Subsequent runs
Each time you want to start the project again:

```
# Open cmd
# Navigate to the project root
.\.venv\Scripts\Activate
python manage.py runserver
```
