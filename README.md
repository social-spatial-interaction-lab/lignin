How to Use:

1.Enter the project directory.

2.Install dependencies according to requirements.

3.Set environment variables. For Windows users, enter the following in the console: set DEEPINFRA_API_TOKEN=YourKey.

4.Activate the virtual environment, for example: .\.venv\Scripts\Activate.

5.Run python manage.py runserver 0.0.0.0:8000.

6.Access and interact with the project through your browser.

Notes:

1.In this branch, LLM responses cannot currently be displayed in the main view table. Instead, they are printed in the browser console. Use F12 to open the console and view them.

2.The add/remove question functionality is not yet implemented. For now, the project uses default questions. The specific prompt contents are recorded in the LLM_response.py file.
