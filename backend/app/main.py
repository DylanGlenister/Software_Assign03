import time
from contextlib import asynccontextmanager

from app.core.database import Database as db
#from app.core.account_route import account_route
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

#=== SETUP ===

@asynccontextmanager
async def lifespan(app: FastAPI):
	#Startup
	#app.state.mongodb = MongoDB("mongodb://localhost:27017", "Software_Assign03")
	db.connect()
	yield
	#Shutdown
	#app.state.mongodb.client.close()
	db.disconnect

app = FastAPI(lifespan=lifespan)
api_path = '/api/v1/endpoints'

# Add CORS middleware, required for frontend connection to work
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:3000"], # URL of React application
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
#app.include_router(account_route)

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
			'Path': api_path,
			'Description': 'Test endpoint.'
		}
	} }

@app.get(api_path)
async def base_api():
	'''Displays a message when the api endpoint is reached.'''
	return { 'Result': 'Your\'e did it' }

@app.get(api_path + '/test/sql')
async def test_sql():
	'''Test a sql command.'''
	result = db.test_select()

	output = [f'id: {id}, value: {value}' for (id, value) in result]

	return { 'Result': {
		'Output': output
	} }
