from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_path: str

    database: str
    database_host: str
    database_port: int
    database_username: str
    database_password: str

    secret_key: str
    algorithm: str
    access_token_expire_minutes: int 

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
    
    def reload_settings(self):
        global SETTINGS
        SETTINGS = Settings()

SETTINGS = Settings()