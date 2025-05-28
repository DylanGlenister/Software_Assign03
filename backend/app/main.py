import time
from contextlib import asynccontextmanager

from app.core.database import Database, get_db
from app.utils.settings import SETTINGS
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from app.core.account_route import account_route
from app.core.customer_route import customer_route
from app.core.admin_route import admin_route

#=== SETUP ===

@asynccontextmanager
async def lifespan(app: FastAPI):
	yield

app = FastAPI(
	lifespan=lifespan,
	)

bearer_scheme = HTTPBearer()

# Add CORS middleware, required for frontend connection to work
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"], # URL of React application
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.middleware('http')
async def log_requests(request: Request, call_next):
	'''Log HTTP requests into the console.'''
	start_time = time.time()
	response = await call_next(request)
	process_time = time.time() - start_time
	print(f'Request: {request.url} - Duration: {process_time} seconds')
	return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
	'''Handle HTTP exceptions.'''
	return JSONResponse(
		status_code=exc.status_code,
		content={'Detail': exc.detail, 'Error': 'An error occurred'}
	)

#=== API PATHS ===
app.include_router(account_route)
app.include_router(customer_route)
app.include_router(admin_route)

@app.get('/')
async def root():
	'''Displays a message when viewing the root of the website.'''
	return { 'Result': {
		'Root': {
			'Type': 'GET',
			'Path': '/',
			'Description': 'Display all avaiable endpoints.'
		},
		'Api path': {
			'Type': 'GET',
			'Path': SETTINGS.api_path,
			'Description': 'Test endpoint.'
		}
	} }

@app.get(SETTINGS.api_path)
async def base_api():
	'''Displays a message when the api endpoint is reached.'''
	return { 'Result': 'Your\'e did it' }

@app.get(SETTINGS.api_path + '/test/sql')
async def test_sql(db: Database = Depends(get_db)):
	'''Test a SQL SELECT query from the test table.'''
	result = db.test_select()

	output = [f'id: {id}, value: {value}' for (id, value) in result]

	return {
		'Result': {
			'Output': output
		}
	}

@app.get("/secure-example", dependencies=[Depends(bearer_scheme)])
def secure_example():
    return {"message": "You are authorized"}