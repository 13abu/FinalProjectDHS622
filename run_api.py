import uvicorn
from fastapi import FastAPI
from final_project.config import api_host, api_port
from final_project.api.routes import router

app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host=api_host, port=api_port)