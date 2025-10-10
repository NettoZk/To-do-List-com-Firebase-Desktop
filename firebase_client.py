import requests
import json
import time
from urllib.parse import quote_plus

class FirebaseClient:
    def __init__(self, api_key, project_id):
        self.api_key = api_key
        self.project_id = project_id
        self.id_token = None
        self.local_id = None
        self.refresh_token = None
        
    def sign_up(self, email, password):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        r = requests.post(url, json=payload)
        return r.json()
    
    def sign_in(self, email, password):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        r = requests.post(url, json=payload)
        data = r.json()
        if 'idToken' in data:
            self.id_token = data['idToken']
            self.local_id = data['localId']
            self.refresh_token = data.get('refreshToken')
        return data
    
    def refresh_id_token(self):
        url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        payload = {"grant_type":"refresh_token","refresh_token": self.refresh_token}
        r = requests.post(url, data=payload)
        data = r.json()
        if 'id_token' in data:
            self.id_token = data['id_token']
            self.refresh_token = data['refresh_token']
        return data
    
    def _base_url(self):
        return f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents"
    
    def create_task(self, user_id, doc):
        url = self._base_url() + f"/tarefas"
        body = {"fields": self._to_firestore_fields({**doc, 'user_id': user_id, 'created_at': int(time.time())})}
        headers = {'Authorization': f'Bearer {self.id_token}'}
        r = requests.post(url, json=body, headers=headers)
        return r.json()
    
    def list_tasks(self, user_id):
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents:runQuery"
        query = {
            "structuredQuery": {
                "from": [{"collectionId": "tarefas"}],
                "where": {
                    "fieldFilter": {
                        "field": {"fieldPath": "user_id"},
                        "op": "EQUAL",
                        "value": {"stringValue": user_id}
                    }
                },
                "orderBy": [{"field": {"fieldPath": "created_at"}, "direction": "DESCENDING"}]
            }
        }
        headers = {'Authorization': f'Bearer {self.id_token}'}
        r = requests.post(url, json=query, headers=headers)
        res = r.json()
        print("RESPOSTA COMPLETA DO FIREBASE:", res)
        tasks = []
        for item in res:
            if 'document' in item:
                doc = item['document']
                fid = doc['name'].split('/')[-1]
                tasks.append({'id': fid, **self._from_firestore_fields(doc['fields'])})
        return tasks

    def update_task(self, doc_id, updates: dict):
        base_url = self._base_url() + f"/tarefas/{doc_id}"
        
        params = [('updateMask.fieldPaths', key) for key in updates.keys()]
        
        body = {"fields": self._to_firestore_fields(updates)}
        headers = {'Authorization': f'Bearer {self.id_token}'}
        
        r = requests.patch(base_url, params=params, json=body, headers=headers)
        return r.json()
    
    def delete_task(self, doc_id):
        url = self._base_url() + f"/tarefas/{doc_id}"
        headers = {'Authorization': f'Bearer {self.id_token}'}
        r = requests.delete(url, headers=headers)
        return r.status_code
    
    def get_user_profile(self, user_id):
        url = self._base_url() + f"/users/{user_id}"
        headers = {'Authorization': f'Bearer {self.id_token}'}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            return self._from_firestore_fields(data.get('fields', {}))
        return None
    
    def _to_firestore_fields(self, d: dict):
        out = {}
        for k, v in d.items():
            if isinstance(v, int):
                out[k] = {"integerValue": str(v)}
            elif isinstance(v, float):
                out[k] = {"doubleValue": v}
            elif isinstance(v, bool):
                out[k] = {"booleanValue": v}
            elif v is None:
                out[k] = {"nullValue": None}
            else:
                out[k] = {"stringValue": str(v)}
        return out

    def _from_firestore_fields(self, f: dict):
        d = {}
        for k, v in f.items():
            if 'stringValue' in v:
                d[k] = v['stringValue']
            elif 'integerValue' in v:
                d[k] = int(v['integerValue'])
            elif 'doubleValue' in v:
                d[k] = float(v['doubleValue'])
            elif 'booleanValue' in v:
                d[k] = v['booleanValue']
            elif 'nullValue' in v:
                d[k] = None
            else:
                d[k] = v
        return d
    
    
    
    