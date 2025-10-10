import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTextEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QComboBox, QFileDialog, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('API_KEY')
PROJECT_ID = os.getenv('PROJECT_ID')
SERVICE_ACCOUNT_KEY_PATH = 'serviceAccountKey.json' 

if not API_KEY or not PROJECT_ID:
    print("ERRO: As variáveis de ambiente API_KEY e PROJECT_ID não foram encontradas.")
    print("Verifique se você criou um arquivo .env e o preencheu corretamente.")
    sys.exit(1)

from firebase_client import FirebaseClient

try:
    from admin_tools import init_admin, create_user as admin_create_user
    ADMIN_TOOLS_AVAILABLE = True
except ImportError:
    ADMIN_TOOLS_AVAILABLE = False
    print("AVISO: admin_tools.py não encontrado. Funcionalidades de admin estarão desabilitadas.")


class LoginWindow(QWidget):

    def __init__(self, client: FirebaseClient):
        super().__init__()
        self.client = client
        self.main_window = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('ToDo - Login')
        self.setFixedSize(450, 350)
        
        v_layout = QVBoxLayout()

        v_layout.setContentsMargins(20, 20, 20, 20)
        v_layout.setSpacing(15)

        v_layout.addStretch(1)

        v_layout.addWidget(QLabel('Email:'))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('seu.email@exemplo.com')
        v_layout.addWidget(self.email_input)

        v_layout.addWidget(QLabel('Senha:'))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        v_layout.addWidget(self.password_input)

        login_btn = QPushButton('Entrar')
        login_btn.clicked.connect(self.login)
        v_layout.addWidget(login_btn)

        v_layout.addStretch(1)
        
        self.setLayout(v_layout)

    def login(self):
        email = self.email_input.text()
        senha = self.password_input.text()

        if not email or not senha:
            QMessageBox.warning(self, 'Erro', 'Email e Senha são obrigatórios.')
            return

        auth_data = self.client.sign_in(email, senha)

        if 'idToken' in auth_data:
            user_id = auth_data['localId']
            profile = self.client.get_user_profile(user_id)

            if profile and 'role' in profile:
                user_role = profile['role']
                
                if user_role in ['admin', 'superadmin']:
                    if not ADMIN_TOOLS_AVAILABLE or not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
                        QMessageBox.critical(self, 'Erro de Configuração Admin',
                                             f"O arquivo '{SERVICE_ACCOUNT_KEY_PATH}' não foi encontrado. "
                                             "Funcionalidades de admin não podem ser ativadas.")
                        return
                    init_admin(SERVICE_ACCOUNT_KEY_PATH)

                QMessageBox.information(self, 'Sucesso', f'Login bem-sucedido como: {user_role.upper()}')
                self.hide()
                self.main_window = MainWindow(self.client, user_role)
                self.main_window.show()
            else:
                QMessageBox.critical(self, 'Erro de Perfil', 'Não foi possível obter o perfil do usuário. '
                                     'Verifique se o usuário possui uma função (role) definida no Firestore.')
        else:
            error_message = auth_data.get('error', {}).get('message', 'Erro desconhecido durante o login.')
            QMessageBox.critical(self, 'Erro de Login', error_message)

class RegisterUserDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Cadastrar Novo Usuário')
        layout = QVBoxLayout(self)

        self.email = QLineEdit()
        self.email.setPlaceholderText('Email do novo usuário')
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText('Senha temporária')
        self.display_name = QLineEdit()
        self.display_name.setPlaceholderText('Nome de Exibição')

        layout.addWidget(QLabel('Email:'))
        layout.addWidget(self.email)
        layout.addWidget(QLabel('Senha:'))
        layout.addWidget(self.password)
        layout.addWidget(QLabel('Nome:'))
        layout.addWidget(self.display_name)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_details(self):
        return self.email.text().strip(), self.password.text(), self.display_name.text().strip()

class EditDialog(QDialog):

    def __init__(self, task, client: FirebaseClient):
        super().__init__()
        self.task = task
        self.client = client
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Editar Tarefa')
        v = QVBoxLayout()
        self.titulo = QLineEdit(self.task.get('titulo'))
        v.addWidget(QLabel('Título'))
        v.addWidget(self.titulo)
        v.addWidget(QLabel('Descrição'))
        self.desc = QTextEdit(self.task.get('descricao'))
        v.addWidget(self.desc)
        self.status = QComboBox()
        self.status.addItems(['pendente', 'em andamento', 'concluída'])
        self.status.setCurrentText(self.task.get('status'))
        v.addWidget(QLabel('Status'))
        v.addWidget(self.status)
        
        button_layout = QHBoxLayout()
        save = QPushButton('Salvar Alterações')
        save.clicked.connect(self.save)
        button_layout.addWidget(save)
        
        delete = QPushButton('Deletar Tarefa')
        delete.setStyleSheet("background-color: #ff4d4d; color: white;")
        delete.clicked.connect(self.delete)
        button_layout.addWidget(delete)
        
        v.addLayout(button_layout)
        self.setLayout(v)

    def save(self):
        updates = {
            'titulo': self.titulo.text(),
            'descricao': self.desc.toPlainText(),
            'status': self.status.currentText()
        }
        res = self.client.update_task(self.task['id'], updates)
        
        if 'error' in res:
            error_message = res['error'].get('message', 'Erro desconhecido.')
            QMessageBox.critical(self, 'Erro ao Atualizar', f'Não foi possível salvar as alterações.\n\nCausa: {error_message}')
        else:
            QMessageBox.information(self, 'Sucesso', 'Tarefa atualizada com sucesso.')
            self.accept()

    def delete(self):
        reply = QMessageBox.question(self, 'Confirmar Exclusão', 'Você tem certeza que deseja deletar esta tarefa?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            status_code = self.client.delete_task(self.task['id'])
            
            if status_code == 200 or status_code == 204:
                QMessageBox.information(self, 'Sucesso', 'Tarefa deletada.')
                self.accept()
            else:
                QMessageBox.critical(self, 'Erro ao Deletar', f'Não foi possível deletar a tarefa.\n\nCódigo de status: {status_code}')


class MainWindow(QWidget):

    def __init__(self, client: FirebaseClient, user_role: str):
        super().__init__()
        self.client = client
        self.user_id = client.local_id
        self.user_role = user_role
        self.tasks = []
        self.init_ui()
        self.load_tasks()

    def init_ui(self):
        self.setWindowTitle('ToDo Desktop App')
        self.setGeometry(100, 100, 800, 600)
        
        main_layout = QVBoxLayout()
        top_bar_layout = QHBoxLayout()

        if self.user_role in ['admin', 'superadmin']:
            self.register_btn = QPushButton('Cadastrar Novo Usuário')
            self.register_btn.clicked.connect(self.open_register_user_dialog)
            top_bar_layout.addWidget(self.register_btn)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Pesquisar tarefas por título...')
        top_bar_layout.addWidget(self.search_input)
        
        refresh_btn = QPushButton('Atualizar Lista')
        refresh_btn.clicked.connect(self.load_tasks)
        top_bar_layout.addWidget(refresh_btn)

        export_btn = QPushButton('Exportar para XLSX')
        export_btn.clicked.connect(self.export_xlsx)
        top_bar_layout.addWidget(export_btn)
        
        main_layout.addLayout(top_bar_layout)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.edit_task)
        main_layout.addWidget(self.list_widget)

        form_layout = QHBoxLayout()
        left_form = QVBoxLayout()
        left_form.addWidget(QLabel('Título da Tarefa:'))
        self.titulo_input = QLineEdit()
        left_form.addWidget(self.titulo_input)
        left_form.addWidget(QLabel('Descrição:'))
        self.desc_input = QTextEdit()
        left_form.addWidget(self.desc_input)
        form_layout.addLayout(left_form)

        right_form = QVBoxLayout()
        right_form.addWidget(QLabel('Status:'))
        self.status_input = QComboBox()
        self.status_input.addItems(['pendente', 'em andamento', 'concluída'])
        right_form.addWidget(self.status_input)
        right_form.addWidget(QLabel('Prioridade:'))
        self.prio_input = QComboBox()
        self.prio_input.addItems(['baixa', 'média', 'alta'])
        right_form.addWidget(self.prio_input)
        add_btn = QPushButton('Criar Nova Tarefa')
        add_btn.clicked.connect(self.create_task)
        right_form.addWidget(add_btn)
        form_layout.addLayout(right_form)

        main_layout.addLayout(form_layout)
        self.setLayout(main_layout)

    def load_tasks(self):
        self.list_widget.clear()
        self.tasks = self.client.list_tasks(self.user_id)
        if not self.tasks:
            self.list_widget.addItem("Nenhuma tarefa encontrada.")
            return

        for t in self.tasks:
            item = QListWidgetItem(f"[{t.get('status', 'N/A').upper()}] {t.get('titulo', 'Sem Título')}")
            item.setData(Qt.UserRole, t)
            self.list_widget.addItem(item)

    def create_task(self):
        titulo = self.titulo_input.text()
        if not titulo:
            QMessageBox.warning(self, 'Erro', 'O título da tarefa é obrigatório.')
            return
            
        doc = {
            'titulo': titulo,
            'descricao': self.desc_input.toPlainText(),
            'status': self.status_input.currentText(),
            'prioridade': self.prio_input.currentText(),
            'due_date': ''
        }
        self.client.create_task(self.user_id, doc)
        QMessageBox.information(self, 'Sucesso', 'Nova tarefa criada.')
        # Limpa os campos do formulário
        self.titulo_input.clear()
        self.desc_input.clear()
        self.load_tasks()

    def edit_task(self, item: QListWidgetItem):
        task_data = item.data(Qt.UserRole)
        if not task_data:
            return
            
        dialog = EditDialog(task_data, self.client)
        dialog.exec_()
        self.load_tasks() 

    def export_xlsx(self):
        if not self.tasks:
            QMessageBox.warning(self, 'Exportar', 'Não há tarefas para exportar.')
            return

        df = pd.DataFrame(self.tasks)
        fname, _ = QFileDialog.getSaveFileName(self, 'Salvar Arquivo XLSX', os.getcwd(), 'Excel Files (*.xlsx)')
        if fname:
            try:
                df.to_excel(fname, index=False)
                QMessageBox.information(self, 'Exportado com Sucesso', f'Arquivo salvo em: {fname}')
            except Exception as e:
                QMessageBox.critical(self, 'Erro ao Exportar', str(e))

    def open_register_user_dialog(self):
        dialog = RegisterUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            email, password, name = dialog.get_details()
            if not email or not password or not name:
                QMessageBox.warning(self, 'Campos Vazios', 'Todos os campos são obrigatórios para criar um usuário.')
                return
            
            try:
                new_user = admin_create_user(email, password, name)
                QMessageBox.information(self, 'Sucesso', f'Usuário criado com sucesso!\nEmail: {email}\nUID: {new_user.uid}')
            except Exception as e:
                QMessageBox.critical(self, 'Erro ao Criar Usuário', f'Não foi possível criar o usuário.\n\nFirebase error: {e}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    app.setStyleSheet("""
        QWidget {
            background-color: #2e2e2e;
            color: #e0e0e0;
            font-family: Segoe UI, sans-serif;
            font-size: 10pt;
        }
        QPushButton {
            background-color: #555;
            color: #fff;
            border: 1px solid #666;
            padding: 8px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #666;
        }
        QPushButton:pressed {
            background-color: #444;
        }
        QLineEdit, QTextEdit, QComboBox { /* <-- EDITE AQUI */
            background-color: #444;
            border: 1px solid #666;
            padding: 8px 10px; /* Aumentado o padding para 8px vertical e 10px horizontal */
            border-radius: 4px;
            min-height: 28px; /* Adicionado altura mínima para LineEdit e ComboBox */
        }
        QListWidget {
            background-color: #3c3c3c;
            border: 1px solid #666;
            border-radius: 4px;
        }
        QLabel {
            font-weight: bold;
        }
        QMessageBox {
            background-color: #3c3c3c;
        }
    """)
    
    client = FirebaseClient(API_KEY, PROJECT_ID)
    login = LoginWindow(client)
    login.show()
    sys.exit(app.exec_())