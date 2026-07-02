import os
import sys
import traceback
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

# Fallback app in case the real app crashes on import
app = FastAPI(title="AiON API (Debug Fallback)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

startup_error = "No error. The app booted successfully."

try:
    # Attempt to import the real app
    from backend.api_real import app as real_app
    
    # If successful, override the fallback app with the real app
    app = real_app
    print("Real API loaded successfully!")
    
    # We still add the /debug route to the real app just in case
    @app.get("/debug")
    def debug_info_real():
        return PlainTextResponse("Real app is running perfectly.")
        
except Exception as e:
    # If it crashes, we capture the full stack trace
    startup_error = traceback.format_exc()
    print("[ERROR] Real API failed to load!")
    try:
        print(startup_error)
    except:
        pass
    
    @app.get("/")
    def health_fallback():
        return {"status": "error", "message": "Backend crashed on startup. See /debug for details."}
        
    @app.get("/debug")
    def debug_info():
        return PlainTextResponse(startup_error)
        
    @app.get("/debug/env")
    def debug_env():
        s_url = os.getenv("SUPABASE_URL", "NOT_SET")
        s_secret = os.getenv("SUPABASE_JWT_SECRET", "NOT_SET")
        if s_secret != "NOT_SET": s_secret = s_secret[:5] + "..." + s_secret[-5:]
        return {"SUPABASE_URL": s_url, "SUPABASE_JWT_SECRET": s_secret}
    
    # Catch-all for API routes to explain why it's down
    @app.api_route("/{path_name:path}", methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"])
    async def catch_all(path_name: str):
        return PlainTextResponse(f"API is down due to startup error: {startup_error}", status_code=500)
