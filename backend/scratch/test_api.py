import urllib.request
import urllib.parse
import json

data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
req = urllib.request.Request('http://localhost:8000/api/auth/login', data=data)
response = urllib.request.urlopen(req)
token = json.loads(response.read().decode())['access_token']

req2 = urllib.request.Request('http://localhost:8000/api/simulation/cases')
req2.add_header('Authorization', f'Bearer {token}')
response2 = urllib.request.urlopen(req2)
print("Status Code:", response2.getcode())
print("Response:", response2.read().decode())
