from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import os
import dotenv
import secrets

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
ADMIN_ROLE_NAME = os.getenv("ADMIN_ROLE_NAME")
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
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

def isPterodactylPasswordKnown(uuid):
    return pterodactylLogins[uuid] is not None

pterodactylLogins = {}
def getPterodactylPassword(uuid):
    if not isPterodactylPasswordKnown(uuid):
        pterodactylLogins[uuid] = secrets.token_hex(24)
    return pterodactylLogins[uuid]

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
    # --- Perform Just-in-Time provisioning here ---
    pwChange = isPterodactylPasswordKnown(token['userinfo']['sub'])
    
    pterodactylUser.createOrUpdate(
        uuid=token['userinfo']['sub'], 
        email=token['userinfo']['email'], 
        username=token['userinfo']['preferred_username'], 
        name=token['userinfo']['name'], 
        password=getPterodactylPassword(token['userinfo']['sub']), 
        isSuperUser=ADMIN_ROLE_NAME in token['userinfo']['groups'],
        pwChange=pwChange)
    
    # --- Perform login to Pterodactyl ---
    session = pterodactyl_session.getPterodactylSession(
        panelURL=PANEL_URL, 
        login=token['userinfo']['email'],
        password=getPterodactylPassword(token['userinfo']['sub']))
    
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
    logout_url = OIDC_END_SESSION_ENDPOINT 
    request.session.clear()
    return RedirectResponse(url=logout_url)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)