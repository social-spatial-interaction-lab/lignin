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

About Development:

1.This version is modified based on the paper-functionality version.

2.Changes in this version include:

    1) templates/ligninapp/question.html: added the Generate Answer button element and front-end script.

    2) urls.py & views.py: added a response handler for the Generate Answer button.

    3) LLM_response.py: located in the same directory as views.py. This file handles prompts and communication with the LLM. It largely follows ai_test.py, but I reorganized the workflow and removed unused code.
