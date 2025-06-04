# Backend
Using fastAPI and uvicorn.
## Setup
**MAKE SURE YOU ARE IN THE `backend` FOLDER**
```bash
cd backend
```
### Create the virtual environment.
```bash
python -m venv .venv
```
### Activate the virtual envionment.
- Windows:
```bash
.\.venv\Scripts\Activate.ps1
```
- Linux, MacOS
```bash
source ./.venv/bin/activate
```
### Install the requirements
```bash
pip install -r requirements.txt
```
### Select the environment
1. With the main.py file open, at the bottom right click the text that says the python version (the right one).
2. Select 'Enter interpreter path...'
3. Enter `./backend/.venv/bin/python`

## Test run
While the current directory is the backend folder:
```bash
uvicorn app.main:app --reload
```
