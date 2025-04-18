import msal
import requests
import time
import jwt
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry, ProtocolError

class ApiClient:
    def __init__(self, tenant_id, client_id, client_secret):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiration = 0
        self.scopes = ["https://graph.microsoft.com/.default"]

        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def get_access_token(self):
        current_time = time.time()
        if self.token and current_time < self.token_expiration:
            print("Using cached access token")
            return self.token

        print("Acquiring new access token")
        app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret,
        )

        token_response = app.acquire_token_for_client(scopes=self.scopes)

        if "access_token" in token_response:
            self.token = token_response["access_token"]
            decoded_token = jwt.decode(self.token, options={"verify_signature": False})
            self.token_expiration = decoded_token.get('exp')
            print(f"Token expires at {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(self.token_expiration))}")
            return self.token
        else:
            raise Exception(f"Could not obtain access token: {token_response.get('error_description')}")

    def query_msgraph(self, base_url=None, params=None, max_retries=5, top=None, page_size=100):
        print(base_url)
        print(params)
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }

        results = []
        retries = 0
        next_link = None
        old_link = None
        records_retrieved = 0

        if max_retries is None:
            max_retries = 3
        
        params = params or {}

        if isinstance(top, int) and top > 0:
            params['$top'] = top

        while True:
            url = next_link if next_link else base_url

            try:
                if next_link:
                    response = self.session.get(url, headers=headers, timeout=10)
                else:
                    response = self.session.get(url, headers=headers, params=params, timeout=10)

                response.raise_for_status()
                data = response.json()
                new_records = data.get("value", [])
                results.extend(new_records)
                records_retrieved += len(new_records)

                if isinstance(top, int) and records_retrieved >= top:
                    break

                next_link = data.get("@odata.nextLink")
                if not next_link or old_link == next_link:
                    break
                old_link = next_link

            except (requests.exceptions.ChunkedEncodingError, ProtocolError, requests.exceptions.RequestException) as e:
                print(f"Request error: {e}, retrying...")
                retries += 1
                if retries > max_retries:
                    raise Exception(f"Max retries exceeded: {e}")
                time.sleep(5)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    retries += 1
                    if retries > max_retries:
                        raise Exception(f"Max retries exceeded: {e}")
                    retry_after = int(e.response.headers.get("Retry-After", 10))
                    print(f"Rate limit hit. Retrying in {retry_after} seconds.")
                    time.sleep(retry_after)
                elif e.response.status_code == 401:
                    print("Token expired. Refreshing...")
                    headers["Authorization"] = f"Bearer {self.get_access_token()}"
                    continue
                elif e.response.status_code == 400:
                    print(f"Bad request: {e}")
                    break
                else:
                    raise

        return results

class PolarApiClient(ApiClient):
    def __init__(self, client_id, client_secret):
        super().__init__(tenant_id="dummy", client_id=client_id, client_secret=client_secret)
        self.token = None
        self.token_expiration = 0

    def get_access_token(self):
        current_time = time.time()
        if self.token and current_time < self.token_expiration:
            print("Using cached access token")
            return self.token

        print("Acquiring new access token from Polar")
        token_url = "https://www.polaraccesslink.com/v3/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = self.session.post(token_url, data=data)
        response.raise_for_status()
        token_response = response.json()
        self.token = token_response.get("access_token")
        expires_in = token_response.get("expires_in")
        self.token_expiration = current_time + int(expires_in)
        print(f"Token expires in {expires_in} seconds")
        return self.token

    def get_exercises(self, user_id):
        access_token = self.get_access_token()
        url = f"https://www.polaraccesslink.com/v3/users/{user_id}/exercises"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_user(self, user_id = None):
        access_token = self.get_access_token()
        url = None
        if user_id is None:
            url = "https://www.polaraccesslink.com/v3/users"
        else:
            url = f"https://www.polaraccesslink.com/v3/users/{user_id}"
            
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    client_id = "f43f6fbc-c6bb-47f7-b5f3-66421037442ayour_polar_client_id"
    client_secret = "y81860b5c-fd24-4583-bf18-91c5c049ef17"
    #user_id = "your_polar_user_id"

    polar_client = PolarApiClient(client_id, client_secret)
    #exercises = polar_client.get_exercises(user_id)
    users = polar_client.get_user()
    print(users)
