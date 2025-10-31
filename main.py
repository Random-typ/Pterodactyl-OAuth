from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import os
import dotenv

import pterodactyl_session
from pterodactyl_user import PterodactylUser

# config
dotenv.load_dotenv()
OIDC_CLIENT_ID = os.getenv('OIDC_CLIENT_ID')
OIDC_CLIENT_SECRET = os.getenv('OIDC_CLIENT_SECRET')
OIDC_DISCOVERY_URL = os.getenv('OIDC_DISCOVERY_URL') 
OIDC_END_SESSION_ENDPOINT = os.getenv('OIDC_END_SESSION_ENDPOINT') 
PANEL_URL = os.getenv('PANEL_URL') 
PTERODACTYL_API = os.getenv('PTERODACTYL_API') 
pterodactylUser = PterodactylUser(PANEL_URL, PTERODACTYL_API)

oauth = OAuth()
oauth.register(
    name='pterodactyl',
    client_id=OIDC_CLIENT_ID, 
    client_secret=OIDC_CLIENT_SECRET,
    server_metadata_url=OIDC_DISCOVERY_URL,
    client_kwargs={'scope': 'openid email profile'}
)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=OIDC_CLIENT_SECRET)

@app.get("/auth/login")
async def sso_login(request: Request, redirect: str | None = None):
    # Store the intended redirect URL from Pterodactyl if it exists
    request.session['final_redirect'] = redirect or '/'
    
    # Start the OIDC flow
    redirect_uri = request.url_for('auth_callback')
    return await oauth.pterodactyl.authorize_redirect(request, redirect_uri)

@app.get('/auth/callback')
async def auth_callback(request: Request):
    token = await oauth.pterodactyl.authorize_access_token(request)
    user_info = await oauth.pterodactyl.parse_id_token(request, token)
    
    input(user_info)

    # --- Perform Just-in-Time provisioning here ---
    pterodactylUser.createOrUpdate()
    
    # --- Perform login to Pterodactyl ---
    session = pterodactyl_session.getPterodactylSession(PANEL_URL, )
    # ptero_session_cookie = perform_pterodactyl_login(user_info['email'], password)
    
    if not session:
        # Handle login failure
        return Response("Failed to log into Pterodactyl.", status_code=500)

    # Redirect to the final destination and set the cookie
    final_url = request.session.pop('final_redirect', '/')
    response = RedirectResponse(url=final_url)
    response.headers.append(key='Set-Cookie', value=session)
    return response

@app.get("/sso/logout")
async def sso_logout(request: Request):
    # This URL is specific to your SSO provider
    logout_url = OIDC_END_SESSION_ENDPOINT 
    # Clear our own session
    request.session.clear()
    return RedirectResponse(url=logout_url)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)