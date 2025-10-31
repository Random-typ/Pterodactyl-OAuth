import requests
import urllib3
from urllib.parse import unquote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

s = requests.Session()
#s.headers.update({
#    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
#    'Accept': 'application/json',
#})
VERIFY_SSL = True

# panelURL: E.g. https://pterodactyl.example.com
# login: username or email
# password: password
# returns empty string on values, otherwise cookies to set
def getPterodactylSession(panelURL, login, password):
    csrf_url = f"{panelURL}/sanctum/csrf-cookie"
    try:
        print(f"[*] GET: Initializing session at {csrf_url}...")
        s.get(csrf_url, verify=VERIFY_SSL).raise_for_status()
        if 'XSRF-TOKEN' not in s.cookies:
            print("[!] Error: Did not receive XSRF-TOKEN cookie.")
            return ''
        print("[+] Success: Received XSRF-TOKEN cookie.")
    except requests.exceptions.RequestException as e:
        print(f"[!] Error on CSRF cookie request: {e}")
        return ''

    login_url = f"{panelURL}/auth/login"
    
    xsrf_token_header_value = unquote(s.cookies['XSRF-TOKEN'])
    
    post_headers = {
        'X-XSRF-TOKEN': xsrf_token_header_value,
        'Referer': login_url,
        'X-Pterodactyl-Route': '1'
    }
    
    payload = {'user': login, 'password': password}

    print(f"[*] POST: Submitting credentials to {login_url}...")
    try:
        post_response = s.post(login_url, json=payload, headers=post_headers, verify=VERIFY_SSL)
        print(f"[*] Response Status Code: {post_response.status_code}")

        if post_response.status_code in [200, 204]:
            print("\n[SUCCESS] Login successful!")
            
            account_url = f"{panelURL}/api/client/account"
            print(f"\n[*] GET: Verifying session by fetching {account_url}...")
            account_info = s.get(account_url, verify=VERIFY_SSL)
            if account_info.status_code == 200:
                print("[+] Verification successful!")
                return s.cookies.get_dict().items()
            else:
                print(f"[!] Verification failed. Status: {account_info.status_code}")
                return ''
        else:
            print("\n[FAILURE] Login failed.")
            print("Response Body:", post_response.text)
            return ''
            
    except requests.exceptions.RequestException as e:
        print(f"[!] Error on login POST request: {e}")
        return ''
