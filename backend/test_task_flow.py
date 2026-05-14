import requests, json

BASE = 'http://localhost:8000/api'

# 1. Login as doctor
r = requests.post(f'{BASE}/auth/login', json={'username': 'dr_smith', 'password': 'doctor123'})
print('Doctor login:', r.status_code)
doctor_data = r.json()
token = doctor_data.get('access_token', '')
if not token:
    print('Login failed:', r.text)
    exit()

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# 2. Get patients
pats = requests.get(f'{BASE}/patients/summary', headers=headers).json()
pid = pats[0]['patient_id']
print(f'Patient id: {pid} (type: {type(pid).__name__})')

# 3. Create task as doctor
task_payload = {
    'patient_id': str(pid),
    'description': 'Administer antibiotics IV',
    'scheduled_time': '08:00',
    'task_type': 'medication',
    'priority': 'high'
}
r2 = requests.post(f'{BASE}/tasks/', json=task_payload, headers=headers)
print('Create task status:', r2.status_code)
print('Created task:', json.dumps(r2.json(), indent=2))

# 4. Login as nurse
r3 = requests.post(f'{BASE}/auth/login', json={'username': 'nurse_jane', 'password': 'nurse123'})
print('\nNurse login:', r3.status_code)
ntoken = r3.json().get('access_token', '')
if not ntoken:
    print('Nurse login failed:', r3.text)
else:
    nheaders = {'Authorization': f'Bearer {ntoken}'}
    tasks = requests.get(f'{BASE}/tasks/', headers=nheaders).json()
    print(f'Nurse sees {len(tasks)} tasks:')
    for t in tasks:
        tid = t.get('id') or t.get('task_id')
        desc = t.get('description', '')
        pat = t.get('patient_id', '')
        pri = t.get('priority', '')
        print(f'  Task {tid}: "{desc}" | patient={pat} | priority={pri}')
