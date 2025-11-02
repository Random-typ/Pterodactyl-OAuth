# Pterodactyl - OAuth
A very basic more or less secure SSO implementation for Pterodactyl Panel.

## How It Works
The default `/auth/login` endpoint that Pterodactyl uses, is redirected to this script. Then a   
normal OAuth using a provider like Authentik to verify user access to Pterodactyl Panel is performed.  
Then the script will check with the Pterodactyl API if the user already exists in Pterodactyl, this  
is done via the `external_id` attribute Pterodactyl provides which is matched with the `sub` attribute  
from the OAuth provider which is a UUID. If a user does not exist it is created with the attributes  
provided by the OAuth provider.   
Then the script checks if it has a password stored for the account that is trying to login, if no it  
update the users password to a newly generated secure password via the Pterodactyl API. These   
passwords are stored at runtime and will be lost once the script/container restarts.  
After finding the password for the Pterodactyl user the script performs a login via the normal   
`/auth/login` Pterodactyl endpoint. The session cookies are then forwarded to the client and the  
client is redirected to Pterodactyl and finally logged in.
If the user changes their name, email or username in the OAuth provider it will also be updated in  
Pterodactyl once the login again using this script. It also checks wether the user has an admin role  
and will give the Pterodactyl user admin accordingly.  
In Pterodactyl the email and username of each user MUST be unique, if a username or email already exists  
a placeholder is used instead.

TL;DR
The user is still logged in via a password and email in the background, the password is long and secure,  
if the user changes their username, name or email it will also change in Pterodactyl, but only when they  
login again using the script. Users will also become admins if they have the matching role set.



### Pterdactyl Two Factor
If two factor is enabled in Pterdactyl, this script will not work.

### Warning
This is not a real Pterodactyl Panel OAuth implementation, but it comes pretty close and is as secure as  
24 character long randomly generated passwords get.


## Migrating Existing Users
Not yet implemented.

## Setup
### Compose
```
services:
  pterodactyl_oauth:
    image: randomtyp/pterodactyl-oauth:latest
    container_name: pterodactyl_oauth
    ports:
      - 8000:8000
    environment:
      - OIDC_CLIENT_ID=              # OAuth provider client id
      - OIDC_CLIENT_SECRET=          # OAuth provider client secret
      - OIDC_DISCOVERY_URL=          # OAuth provider discovery url E.g. https://auth.example.com/application/o/pterodactyl/.well-known/openid-configuration
      - OIDC_END_SESSION_ENDPOINT=   # OAuth provider logout url E.g https://auth.example.com/application/o/pterodactyl/end-session/
      - PANEL_URL=                   # Pterodactyl Panel url E.g https://pterodactyl.example.com/
      - PTERODACTYL_API=             # Pterodactyl API Key. MUST HAVE USERS READ/WRITE PERMISSION
      - ADMIN_ROLE_NAME=             # OAuth provider admin role name E.g authentik Admins
```

### Redirects
The `/auth/login/*`, `/auth/callback/*` and `/sso/logout/*` path must be redirected to the script. 
This route must be bypassed (routed to Pterodactyl) if the `X-Pterodactyl-Route` header is set. 

Example `Traefik` config:
```
  entryPoints:
    - websecure
  routes:
    - match: Host(`pterodactyl.example.com`) && PathRegexp(`^/(auth/(login|callback)|sso/logout)/?.*`) && !HeaderRegexp(`X-Pterodactyl-Route`, `.*`)
      kind: Rule
      priority: 100
      services:
        - name: pterodactyl-sso
          port: 8000
```

### Optional Redirects
The user could still change their password, email or enable two step verification in Pterodactyl. You might  
to prevent this you can redirect the `/account` path to `account/api`, also redirect  `/account/password`,  
`/account/two-factor` and`/account/email` to somewhere else.

### `/auth/login/` Redirect Not Working??
You go to your Pterodactyl Panel, are redirected to `/auth/login/` but still see the normal Pterodactyl  
login screen? This is because Pterodactyl routes to `/auth/login/` with js in the client. To fix the reload  
the page. If you navigate to `/auth/login/` manually it will also work. 

