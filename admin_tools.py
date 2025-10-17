import firebase_admin
from firebase_admin import auth, credentials, firestore
import argparse
import os

def init_admin(service_account_path):
    cred = credentials.Certificate(service_account_path)
    try:
        firebase_admin.initialize_app(cred)
    except Exception:
        pass
    return firestore.client()


def create_user(email, password, display_name=None):
    user = auth.create_user(email=email, password=password, display_name=display_name)
    db = firestore.client()
    db.collection('users').document(user.uid).set({
        'email': email,
        'display_name': display_name or '',
        'role': 'user',
        'created_at': firestore.SERVER_TIMESTAMP
    })
    return user


def set_role(uid, role):
    # role: 'user', 'admin', 'superadmin'
    auth.set_custom_user_claims(uid, {'role': role})
    db = firestore.client()
    db.collection('users').document(uid).update({'role': role})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Ferramentas de admin para o app ToDo com Firebase.")
    parser.add_argument('--service-account', required=True, help='Caminho para o arquivo serviceAccountKey.json')
    parser.add_argument('--create-user', nargs=3, metavar=('email','senha','nome'), help='Cria um novo usuário com perfil no Firestore.')
    parser.add_argument('--set-role', nargs=2, metavar=('uid','role'), help='Define uma role (user, admin, superadmin) para um usuário.')
    args = parser.parse_args()

    if not os.path.exists(args.service_account):
        print(f"\nERRO: O arquivo da chave de serviço '{args.service_account}' não foi encontrado.")
        print("Por favor, baixe o arquivo JSON da chave de serviço do seu projeto no Firebase e tente novamente.")
        exit(1) 

    init_admin(args.service_account)
    
    if args.create_user:
        email, senha, nome = args.create_user
        try:
            u = create_user(email, senha, nome)
            print(f"\nUsuário criado com sucesso!")
            print(f"  Email: {u.email}")
            print(f"  UID: {u.uid}")
        except Exception as e:
            print(f"\nERRO ao criar usuário: {e}")

    if args.set_role:
        uid, role = args.set_role
        try:
            set_role(uid, role)
            print(f"\nRole '{role}' definida com sucesso para o UID: {uid}")
        except Exception as e:
            print(f"\nERRO ao definir a role: {e}")