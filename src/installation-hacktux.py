import ctypes
import json
import os
import psutil
import subprocess
import sys
import threading
import time
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.fernet import Fernet
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
import vrest
import ipaddress
from datetime import datetime, timedelta,timezone
from pathlib import Path

# ! ================================================ AVISOS ====================================================

# ! ============================================================================================================

#==================================================#
#===== Variaveis Globais Utilizadas no SCRIPT =====#
#==================================================#

if getattr(sys, 'frozen', False):
    application_location_base = sys.executable
elif __file__:
    application_location_base = __file__

ERROR_TITLE = "Machine configuration error"
VERSION = "0.2"
progress_percentage = 0
thread_list = []

vmware_directory_path = "C:\\Program Files (x86)\\VMware\\VMware Workstation"
api_rest_executable = "vmrest.exe"
vms_path = os.path.dirname(os.path.dirname(os.path.abspath(application_location_base))) + "\\virtual-machines"
#vms_path = "E:\\ProjetoFinalEI"
cert_path = os.path.dirname(os.path.abspath(application_location_base)) + "\\hacktux-data\\https\\hacktux_cert.crt"
key_path = os.path.dirname(os.path.abspath(application_location_base)) + "\\hacktux-data\\https\\hacktux_private.key"

path_conf_settings = os.path.dirname(os.path.abspath(application_location_base)) + "\\conf-settings.json"
path_vm_json_data = os.path.dirname(os.path.abspath(application_location_base)) + "\\hacktux-data\\virtual-machine-data\\virtual-machines.json"
path_lab_json_data = os.path.dirname(os.path.abspath(application_location_base)) + "\\hacktux-data\\labs-data\\labs.json"

img_path_hacktux = os.path.dirname(os.path.abspath(application_location_base)) + "\\images\\icon-janela-principal-hacktux.png"
img_path_settings = os.path.dirname(os.path.abspath(application_location_base)) + "\\images\\icon-settings.png"
#===========================================#
#===== Funções auxiliares da aplicação =====#
#===========================================#

def exit_application(code):
    """
    (Esta função faz a aplicação terminar
    o code indica o estado com que a aplicação saiu)
    
    0 -> Indica que a aplicação terminou corretamente
    1 -> A aplicação saiu terminou devido a algum erro
    """
    sys.exit(code)

def schedule_check(frame):
    """
    Schedule the execution of the `check_if_done()` function after
    one second.
    """
    #===== De 1 em 1 segundo faz com que a thread da janela verifique se a outra thread ainda se encontra em execução
    frame.after(1000, check_if_done,frame)

def check_if_done(frame):
    """
    - Percorre a lista das threads e verifica se existe alguma que esteja a correr
    caso exista alguma a correr, a thread que apresenta a janela root volta a executar a
    função  'schedule_check()'

    """
    global thread_list
    flag = False
    for t in thread_list:
        if t.is_alive():
            flag = True
            break
    if flag:        
        schedule_check(frame)

def show_error(title_windows,message_window,parent):
    """
    Função que apresenta uma janela de erro com a mensagem predefinida
    e no fim de clicar no ok dessa janela, sai da aplicação
 
    """
    messagebox.showerror(title_windows, message_window, parent=parent)
    exit_application(1)

def show_sucess(title_windows,message_window,parent):
    """
    Função que apresenta uma janela de sucesso com a mensagem predefinida
    e no fim de clicar no ok dessa janela, sai da aplicação
 
    """
    messagebox.showinfo(title_windows, message_window, parent=parent)
    exit_application(0)

def show_executation_state(text_box,progress_bar,message,parent):
    """
    Função utilizada para apresentar na janela root os avanços da 
    configuração/instalação do hacktux.
    - Escreve a mensagem a indicar o que fez
    - Avança a barra de progresso 
    """
    global progress_percentage

    text_box.config(state=tk.NORMAL)
    text_box.insert(tk.END, message)
    text_box.config(state=tk.DISABLED)

    progress_bar['value'] = progress_percentage
    parent.update_idletasks()

def configuration_vms(text_box, progress_bar, accept_button, parent):
    """
    Função utilizada para configurar as maquinas, dentro dela estão todos os
    passos necessários para configurar as máquinas
    """

    #============================================================#
    #===== Funções auxiliares da função "configuration_vms" =====#
    #============================================================#

    def register_vm(vm_path, vm_name,text_box):
        global ERROR_TITLE
        #===== Regista a VM no Vmware Workstation do utilizador
        vmregister = vrest.register_vm({"id": '', "path": vm_path, "name": vm_name})
        
        #===== Valida qual foi a resposta da API
        if vmregister['status'] == 201:
            #===== Apresenta ao utilizador que conseguio registar a VM 
            parent.after(0, show_executation_state,text_box,progress_bar,f" (*) VM {vm_name} has been registered -> (Success)\n",parent)
            return 0

        elif vmregister['status'] == 500 and vmregister['data']['Code'] == 147:
            #===== Apresentao ao utilizador que a VM já se encontra registada
            parent.after(0, show_executation_state,text_box,progress_bar,f" (*) VM {vm_name} is already registered -> (Success)\n",parent)
            return 0

        else:
            #===== Apresentao ao utilizador que surgiu um problema ao registar a VM
            parent.after(0, show_error,ERROR_TITLE,f"Unable to register VM {vm_name} in VMware Workstation",parent)
            return -1

    def check_machines(vms_info, vm_path):        
        for item in vms_info['data']:
            if item['path'] == vm_path:
                return item['id']
        return -1

    def associate_vm_vmnet(vm_id, vm_name, vmnet_number, params):
        global ERROR_TITLE
        #===== Associa uma NIC de uma máquina a uma VMNET especifica
        associate = vrest.update_nic(vm_id, vmnet_number, params)
        
        #===== Verifica qual foi o estado do pedido
        if associate['status'] == 200:
            vmnet_name = params["vmnet"]
            parent.after(0, show_executation_state,text_box,progress_bar,f" (*) The NIC {vmnet_number} of the VM {vm_name} has been connected to \'{vmnet_name}\'-> (Success)\n",parent)
            return 0
        
        #===== Apresenta um ERRO caso não consiga associar a nic a uma determinada interface
        else:
            parent.after(0, show_error,ERROR_TITLE,f"Could not connect NIC {vmnet_number} of VM {vm_name} to \'{vmnet_name}\'",parent)
            return -1
        
    def cert_generator():
        global key_path
        global cert_path
        emailAddress = "2211049@my.ipleiria.pt | 2211089@my.ipleiria.pt"
        commonName = "Hacktux"
        countryName = "NT"
        localityName = "leiria"
        stateOrProvinceName = "leiria"
        organizationName = "IPLeiria"
        organizationUnitName = "ESTG"
        validityStartInSeconds = 0
        validityEndInSeconds = 10 * 365 * 24 * 60 * 60
        san_ip = "127.0.0.1"
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, countryName),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, stateOrProvinceName),
            x509.NameAttribute(NameOID.LOCALITY_NAME, localityName),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organizationName),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, organizationUnitName),
            x509.NameAttribute(NameOID.COMMON_NAME, commonName),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, emailAddress),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc) + timedelta(seconds=validityStartInSeconds)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(seconds=validityEndInSeconds)
        ).add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.IPv4Address(san_ip))]),
            critical=False,
        ).sign(private_key, hashes.SHA512())
        
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        
    def front_end_modifications(accept_button,text_box):
        #===== Modificações do FrontEnd
        #======= Desativar botão de aceitar
        accept_button.config(state=tk.DISABLED)

        #======= Eliminar o texto que se encontra na text Box e criar 
        text_box.config(state=tk.NORMAL)
        text_box.delete("1.0", tk.END)
        text_box.config(state=tk.DISABLED)

    #==========================================================#
    #===== Inicio da Função da função "configuration_vms" =====#
    #==========================================================#

    #===== Parametrização das variaveis para indicar que estas se referem às variaveis globais
    global ERROR_TITLE
    global progress_percentage
    global path_conf_settings 
    global vmware_directory_path
    global api_rest_executable
    global vms_path
    global path_vm_json_data
    global path_lab_json_data
    global application_location_base
    #===== Limpar caixa de texto da janela root, e desativar botão de aceitar
    parent.after(0, front_end_modifications,accept_button,text_box)
    
    #===============================================================================#
    #===== 0 - Carregar os dados do ficheiro conf-settings para a aplicação ========#
    #===============================================================================#

    #===== Código para carregar os dados do ficheiro JSON de configuração
    try:
        #===== Abre o ficheiro conf-settings em modo leitura e com um econding em UTF-8
        with open(path_conf_settings,"r",encoding="utf-8") as file:
            conf_settings_data = json.load(file)

    except FileNotFoundError:
        #===== Apresenta erro caso o ficheiro não seja encontrado na diretoria
        parent.after(0, show_error,ERROR_TITLE,"Could not find file \'conf-settings.json\' in executable directory",parent)
        return

    except Exception as e:
        #===== Apresenta erro caso não seja possível abrir o ficheiro
        parent.after(0, show_error,ERROR_TITLE,f"Unable to load data from file \'conf-settings.json\' {e}",parent)
        return

    #======================================================================#
    #===== 1 - Copiar Ficheiro Hacktux para a diretoria do utilizador =====#
    #======================================================================#
    
    #===== Executa o programa whoami para obter o nome da conta user do utilizador que está a correr o programa 
    try:
        result = subprocess.run(['whoami'], capture_output=True, text=True, check=True)

    except Exception as e:
        #===== Apresenta erro caso não seja possível obter o nome
        parent.after(0, show_error,ERROR_TITLE,f"Unable to get windows user name",parent)
        return
    
    #===== Depois de obtido o nome este é tratado para ficar na variavel username
    full_user_name = result.stdout.strip()
    username = full_user_name.split('\\')[-1]

    #===== Depois de obtido a o nome da variavel é criado a varivel com o caminho para a pasta do user
    home_dir = f"C:\\Users\\{username}"

    #===== Verifica se no sistema existe esse caminho, caso exista prossegue, se não vai verificar que diretoria estava no ficheiro conf-settings
    if not os.path.exists(home_dir):
        home_dir = conf_settings_data['user_home_directory_path']

        #===== Caso não exista a diretoria home que o user coloco no ficheiro é apresentado uma mensagem de erro
        if not os.path.exists(home_dir):
            parent.after(0, show_error,ERROR_TITLE,"The user's home directory could not be found",parent)
            return
    
    #===== Copie o ficheiro para o diretório home do utilizador
    src_file = os.path.dirname(os.path.abspath(application_location_base)) + "\\vmrest.cfg"
    dest_file = os.path.join(home_dir, "vmrest.cfg")

    #===== Executa o proframa copy para copiar o ficheiro vmrest.cfg para a diretoria home do utilizador
    try:
        subprocess.run(['copy', src_file, dest_file], shell=True, check=True)

    except Exception as e:
        #===== Caso não seja possível copiar é apresentado o erro
        parent.after(0, show_error,ERROR_TITLE,f"Unable to copy 'vmrest' file to user's home directory",parent)
        return
    
    #===== Verificação se a cópia se realizou realmente
    if not os.path.exists(dest_file):
        parent.after(0, show_error,ERROR_TITLE,f"Unable to copy 'vmrest' file to user's home directory",parent)
        return

    progress_percentage = progress_percentage + 17
    parent.after(0, show_executation_state,text_box,progress_bar,f" (*) Copy file \'vmrest.cfg\' to {home_dir} -> (Success)\n",parent)

    #================================================================#
    #===== 2 - Colocar a API REST do VMWARE Workstatio a funcionar ==#
    #================================================================#
    cert_generator()
    #===== Tentar encontrar a diretoria do VMware Workstation, começa por ver a diretoria default do VMware
    #===== Verifica se a diretoria existe no sistema, se existir avança, se não vai verificar ao ficheiro conf-settings
    if not os.path.exists(vmware_directory_path):
        vmware_directory_path = conf_settings_data['vmware_directory_path']

        #===== Verifica se a diretoria que está no ficheiro conf-settings existe no sistema, se existir avança, se não apresenta um erro
        if not os.path.exists(vmware_directory_path):
            parent.after(0, show_error,ERROR_TITLE,"Could not find the VMware Workstation directory",parent)
            return

    #===== Tentar encontrar o executável da API do VMware Workstation
    executable_path = os.path.join(vmware_directory_path, api_rest_executable)
    executable_components ="-c \"" + cert_path+ "\" -k \"" + key_path + "\""
    #===== Caso não exista o executável na diretoria é apresentado uma mensagem de erro
    if not os.path.exists(executable_path):
        parent.after(0, show_error,ERROR_TITLE,"The VMware Workstation REST API executable could not be found",parent)
        return
    
    #===== Vai verificar se a API REST do VMware já se encontra a correr se sim termina o processo devido aos certeficados
    for proc in psutil.process_iter(attrs=['name']):
        if proc.info['name'] == api_rest_executable:
            proc.kill()
            break
    
    try:
        #===== Executa uma funcção do windows em C que permite executar aplicações com provilegios de Admin
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable_path, executable_components, None, 0)

        #===== Verificar qual foi o resultado da Função
        if ret == 5:
            parent.after(0, show_error,ERROR_TITLE,f"To configure the machines, you must allow \'vmrest\' to run with administrator privileges",parent)
            return
        
        elif ret < 32:
            parent.after(0, show_error,ERROR_TITLE,f"Unable to run the VMware Workstation REST API executable",parent)
            return

    except Exception as e:
        parent.after(0, show_error,ERROR_TITLE,f"Unable to run the VMware Workstation REST API executable, {e}",parent)
        return

    progress_percentage = progress_percentage + 17
    parent.after(0, show_executation_state,text_box,progress_bar,f" (*) Start the VMware Workstation REST API -> (Success)\n",parent)

    #=================================================================================================#
    #===== 3 - Autenticação na API REST do VMware Workstation, por causa de atrasos tenta 5 vezes ====#
    #=================================================================================================#

    #===== Criar instancia do Fernet
    fernet = Fernet(conf_settings_data["key"].encode())

    #===== Ir buscar ao ficheiro de configuração os dados para a autenticação
    rest_api_username = fernet.decrypt(conf_settings_data["VMWPRAPI-username"].encode()).decode()
    rest_api_password = fernet.decrypt(conf_settings_data["VMWPRAPI-password"].encode()).decode()

    #===== Realiza um pedido à API do VMware REST
    status=vrest.authenticate(rest_api_username, rest_api_password)
    
    #===== Verificação para testar se a autenticação foi realizada, testa durante 5 vezes se consegue autenticar e espera 1 segundo após cada tentativa  
    auth_attempts = 0
    while(status != 200):

        if auth_attempts > 4:
            parent.after(0, show_error,ERROR_TITLE,f"Unable to authenticate to VMware Workstation REST API, maximum attempts exceeded",parent)
            return

        auth_attempts += 1
        time.sleep(1)
        status=vrest.authenticate(rest_api_username, rest_api_password)
    

    progress_percentage = progress_percentage + 17
    parent.after(0, show_executation_state,text_box,progress_bar,f" (*) Authenticate to the VMware Workstation REST API -> (Success)\n",parent)

    
    #============================================================================================================#
    #===== 4 - Ir buscar as carcterisitcas das máquinas e dos laboratorios à diretoria das máquinas virtuais ====#
    #============================================================================================================#

    #===== Colocar numa lista o caminho para os ficheiros .hacktux.json e noutra lista os ficheiros.vmx
    try:
        #===== Ficheiros .hacktux.json
        command = f"dir \"{vms_path}\" /b /s | findstr \\.hacktux.json$"  
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        settings_vms_path_list = result.stdout.strip().split("\n")

        #===== Ficheiros .vmx
        command = f"dir \"{vms_path}\" /b /s | findstr \\.vmx$"  
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        vmx_vms_path_list = result.stdout.strip().split("\n")

    except Exception as e:
        #===== Apresenta um erro caso não seja possível obter algum dos caminhos
        parent.after(0, show_error,ERROR_TITLE,f"It was not possible to obtain the definitions of the virtual machines. {e}",parent)
        return

    #===== Variaveis que vai armazenar os dados dos ficheiros JSON
    vms_json = {}
    vms_json["vms"] = []

    labs_json = {}
    labs_json["labs"] = []
    
    #===== Ir a cada ficheiro, buscar os dados de cada vm e labs e colocar esses dados todos juntos guardados noutros ficheiros
    try:
        #===== Carrega os configurações de cada máquina virtual e da seus labs
        for item in settings_vms_path_list:
            with open(item, "r",encoding="utf-8") as file:
                vm_data = json.load(file)

            #===== Verifica se o caminho do vmx é igual ao caminho do ficheiro.hacktux.json
            for i in vmx_vms_path_list:
                if os.path.dirname(os.path.abspath(i)) == os.path.dirname(os.path.abspath(item)):
                    path = Path(i)
                    path_driver = path.drive.upper() 
                    path_aux = path.as_posix()[len(path.drive):]
                    path = Path(path_driver + path_aux)
                    vm_data["vm"]["path"] = str(path)
                    break
            
            #===== Adiciona à variável a VM 
            vms_json["vms"].append(vm_data["vm"])

            #===== Vai inserir o laboratorio se este ainda não estiver colocado na variavel labs_json
            for lab in vm_data["labs"]:
                flag_lab = True
                for id in labs_json["labs"]:
                    if lab["id"] == id["id"]:
                        flag_lab = False
                        break
                
                if flag_lab:
                    labs_json["labs"].append(lab)                        

    except Exception as e:
        parent.after(0, show_error,ERROR_TITLE,f"It was not possible to obtain the definitions and labs of the virtual machines. {e}",parent)
        return

    #===============================================================#
    #===== 6 - Percorrer o array com as VMS e registar as vms ======#
    #===============================================================#

    for item in vms_json["vms"]:
        if register_vm(item["path"],item["name"],text_box) == -1:
            return


    #===== Avança a barra de progresso
    progress_percentage = progress_percentage + 17
    parent.after(0, show_executation_state,text_box,progress_bar,"",parent)

    #=================================================================================================================#
    #===== 7 - Guardar os dados das VMS nos ficheiros em conjunto com o ID colocado pelo vmware workstation ==========#
    #=================================================================================================================#

    #===== Ir buscar o id das VMS do Hacktux
    vms_info = vrest.get_vms()

    for item in vms_json["vms"]:
        its_id = check_machines(vms_info, item["path"])

        if its_id != -1:
            item["id-workstation"] = its_id
        else:
            parent.after(0, show_error,ERROR_TITLE,"Unable to obtain VM workstation id "+ item["name"],parent)
            return

    #===== Vai colocar no ficheiro labs.json o caminho e o id do workstation
    for virtualmachine in vms_json["vms"]:
        for laboratory in labs_json["labs"]:
            for vm in laboratory["vms-necessary"]:
                if vm["id-hacktux"] == virtualmachine["id-hacktux"]:
                    vm["path"] = virtualmachine["path"]
                    vm["id-workstation"] = virtualmachine["id-workstation"]
                    break
    
    #===== Abre o ficheiro e escreve os dados que estão na variàvel
    try:
        with open(path_vm_json_data,"w",encoding="utf-8") as file:
            json.dump(vms_json,file,indent=4)

    except Exception as e:
        parent.after(0, show_error,ERROR_TITLE,f"It was not possible to save the definitions of the virtual machines in the file \'virtual-machines.json\' .",parent)
        return
    
    #===============================================================#
    #===== 5 - Guardar esses dados dos laboratorios num ficheiro ===#
    #===============================================================#
    
    #===== Abre o ficheiro e escreve os dados que estão na variàvel
    try:
        with open(path_lab_json_data,"w",encoding="utf-8") as file:
            json.dump(labs_json,file,indent=4)

    except Exception as e:
        parent.after(0, show_error,ERROR_TITLE,f"It was not possible to save the labs of the virtual machines in the file \'labs.json\' .",parent)
        return

    #=======================================================#    
    #===== 8 - Criar a VMNET para as Máquinas Virtuais =====#
    #=======================================================#
    
    #===== Mostra todas as Vmnets existentes e vai buscar a ultima VMNET
    vmnets_online = vrest.get_vmnets()
    last_vm_name = vmnets_online['data']['vmnets'][-1]['name']

    #===== Calcula o numero para a VMNET do HACKTUX
    vmnet_number = int(last_vm_name.split("vmnet")[1])
    vmnet_hacktux = "vmnet" + str(vmnet_number + 1)

    #Criar a vmnet do HACKTUX
    create_vmnet = vrest.create_vmnet({ "name": vmnet_hacktux, "type": "hostOnly"})
    if create_vmnet['status'] != 201:
        parent.after(0, show_error,ERROR_TITLE,f"Unable to create VMNET {vmnet_hacktux} to connect the Machines to each other,{create_vmnet['data']['Message']}",parent)
        return
    
    #===== Se chager aqui quer dizer que foi sucesso
    #===== Indicar ao utilizador que conseguio criar a VMNET
    progress_percentage = progress_percentage + 17
    parent.after(0, show_executation_state,text_box,progress_bar,f" (*) Create vmnet \'{vmnet_hacktux}\' for virtual machine communication -> (Success)\n",parent)
    
    #================================================#
    #===== 9 - associate VMs do Hacktux à VMNET =====#
    #================================================#

    for item in vms_json["vms"]:
        if associate_vm_vmnet(item["id-workstation"],item["name"],item["hacktux-nic"],{"type": "custom", "vmnet": vmnet_hacktux}) == -1:
            return

    #===== Avança a barra de progresso
    #===== Avança a barra de progresso
    progress_percentage = progress_percentage + 17
    parent.after(0, show_executation_state,text_box,progress_bar,"",parent)

    #Se chegar aqui quer dizer que foi possível configurar com suscesso o hacjtux
    parent.after(0, show_executation_state,text_box,progress_bar,f" !!! Hacktux configuration successfully completed !!! \n",parent)

    #====================================================================================================#
    #===== 10 - Mensagem de sucesso a indicar que a aplicação foi configurada/instalada com sucesso =====#
    #====================================================================================================#

    parent.after(0,show_sucess,"Hacktux Instalation Success","The Machines and Hacktux have been successfully configured",parent)
    return

def start_configuration_vms(text_box, progress_bar, accept_button, parent):
    global thread_list
    #===== Criação da Thread que vai tratar de configurar as máquinas, recebe a função que deve executar e os argumentos da mesma
    thread = threading.Thread(target=configuration_vms, args=(text_box,progress_bar,accept_button,parent))
    thread_list.append(thread)
    #===== Define a Thread com o daemon a True, isto faz com que caso o processo, ou thread principal seja terminado, a thread que se cria também termina
    thread.daemon= True
    #===== Inicia a execução da thread
    thread.start()
    #===== Inica o loop de verificações por parte da thread principal, a que apresenta a janela, para verificar se a thread que é criada no programa ainda se encontra em execução
    schedule_check(parent)

def choose_folder(entry,parent):
    folder = filedialog.askdirectory(parent=parent)
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)

def save_settings(parent,folder_entry,folder_entry2):
    global path_conf_settings
    
    response = messagebox.askquestion("Save configuration?", "Are you sure you want to save the configuration?", parent=parent)
    if response == "no":
        return
    new_vmware_path = folder_entry.get()
    new_home_path = folder_entry2.get()

    # Load existing configuration or create a new structure if the file does not exist
    if os.path.isfile(path_conf_settings):
        with open(path_conf_settings, 'r', encoding="utf-8") as file:
            configuration = json.load(file)
    
    else:
        configuration = {
            "user_home_directory_path": "",
            "vmware_directory_path": "",
            "VMWPRAPI-username": "gAAAAABmmj87587c8ygnY3L_bYS3P6vLhdc_-MzkZY9esSD_r1r_He-15YAUwcOMW0xhO3oG8KDDPfaVUn-LZl8yYjoIsvRDxQ==",
            "VMWPRAPI-password": "gAAAAABmmj87ki6RN_cRItopofAdl8x7RO9Cxx67N1i7o--T4OCWJeORv0e8MdEFB2OWP47t5OfUpPEuc4_Luq9WJ0_vZgzVmA==",
            "key": "VxHnEe8-jhTKQ4pplQfPLUcy2_65kZQ4e4EpPDAJ3MY=",
            "error_message": "true"
        }

    # Change only the "vmware_directory_path" field
    configuration["vmware_directory_path"] = new_vmware_path
    configuration["user_home_directory_path"] = new_home_path

    try:
        # Save the configuration back to the JSON file
        with open(path_conf_settings, 'w') as file:
            json.dump(configuration, file, indent=4)
    
    except Exception as e:
        messagebox.showerror("Error writing data to file",f"The data could not be saved in the \'conf-settings\' file ({e})",parent=parent)
        return
    
    # Update the status label
    messagebox.showinfo("Success!", "The configuration has been saved successfully!", parent=parent)

    parent.destroy()

def show_window_settings(father_window):
    global img_path_hacktux

    window_settings = tk.Toplevel(father_window)
    window_settings.title("Change Hacktux settings")
    icon_image = tk.PhotoImage(file=img_path_hacktux)
    window_settings.iconphoto(True, icon_image)

    window_settings.grab_set()

    # Adjust the window size
    window_settings.geometry("600x400")
    window_settings.resizable(False, False)

    # Style for widgets
    font_style = ("Helvetica", 12)
    title_font_style = ("Helvetica", 14, "bold")

    top_bar = tk.Frame(window_settings, bg="gray", height=50)
    top_bar.pack(fill=tk.X)

    # Add title to the top bar
    title_label_bar = tk.Label(top_bar, text="Settings", font=title_font_style, bg="gray", fg="white")
    title_label_bar.pack(pady=10)

    # Main frame
    main_frame = tk.Frame(window_settings, padx=20, pady=20)
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Label for instruction
    folder_label = tk.Label(main_frame, text="Choose the directory of your VMware Workstation:", font=font_style)
    folder_label.pack() 

    folder_entry = tk.Entry(main_frame, width=50, font=font_style)
    folder_entry.pack(pady=5)

    # Button to open the folder selection dialog
    choose_button = tk.Button(main_frame, text="Choose folder", font=font_style, command=lambda:choose_folder(folder_entry,window_settings))
    choose_button.pack(pady=10)

    # Choose the path for the home directory
    home_folder_label = tk.Label(main_frame, text="Choose the user's home directory:", font=font_style)
    home_folder_label.pack()

    folder_entry2 = tk.Entry(main_frame, width=50, font=font_style)
    folder_entry2.pack(pady=5)

    # Button to open the folder selection dialog
    choose_button2 = tk.Button(main_frame, text="Choose folder", font=font_style, command=lambda:choose_folder(folder_entry2,window_settings))
    choose_button2.pack(pady=10)

    # Button to save the configuration
    save_button = tk.Button(main_frame, text="Save settings", font=font_style,command=lambda:save_settings(window_settings,folder_entry,folder_entry2))
    save_button.pack(pady=20)

    father_window.wait_window(window_settings)

    

#===================================#
#===== Função principal main() =====#
#===================================#

def main():
    global VERSION
    global img_path_hacktux
    global img_path_settings
    #===== Criação do da Página Principal do Wizard
    root = tk.Tk()
    #===== Parâmetros da Página Principal
    root.title(f"Hacktux Installer - Version: {VERSION}")
    #===== Comprimento X Largura (with X height)
    root.geometry("600x500")
    #===== Bloqueia a opção de o tulizador maximizar a janela
    root.resizable(False, False)
    #===== Coloca como icon a imagem do Hacktux
    main_image = tk.PhotoImage(file=img_path_hacktux)
    root.iconphoto(False, main_image)

    #===== Divisão da janela principal em 3 zonas , TOPO, MEIO, FUNDO
    frame_top = tk.Frame(root, height=150)
    frame_middle = tk.Frame(root, height=300)
    frame_bottom = tk.Frame(root, height=50)

    frame_top.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    frame_middle.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    frame_bottom.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    #===== Parâmetros da Imagem
    frame_image = tk.Frame(frame_top, width=200, height=150)
    frame_image.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) 
    #===== Parametros para colocar a imagem na janela
    image_label = tk.Label(frame_image, image=main_image)
    image_label.pack()

    #===== Parâmetros do Titulo
    frame_title = tk.Frame(frame_top, width=400, height=50)
    frame_title.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    frame_title_and_button = tk.Frame(frame_title, width=400, height=25)
    frame_title_and_button.pack(fill=tk.BOTH)
    frame_description = tk.Frame(frame_title, width=400, height=25)
    frame_description.pack(fill=tk.BOTH)

    label_title = tk.Label(frame_title_and_button, text="Hacktux", font=("Helvetica", 32, "bold"),width=13)
    label_title.pack(pady=10,side=tk.LEFT,expand=True)


    button_settings_image = tk.PhotoImage(file=img_path_settings)
    button_settings = tk.Button(frame_title_and_button,image=button_settings_image,bd=1,highlightthickness=1,bg="white",command=lambda:show_window_settings(root))
    button_settings.pack(side=tk.RIGHT,padx=5)
    
    label_version = tk.Label(frame_description, text=f"Configuring Virtual Machines - Version {VERSION}", font=("Helvetica", 16, "bold"), width=400)
    label_version.pack(pady=10)

    #===== Parâmetros do Texto
    text_box = tk.Text(frame_middle, wrap=tk.WORD, state=tk.DISABLED, width=20, height=19)
    text_box.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    scroll_bar = tk.Scrollbar(frame_middle, orient=tk.VERTICAL, command=text_box.yview)
    scroll_bar.grid(row=0, column=1, sticky=(tk.N, tk.S))

    text_box.config(yscrollcommand=scroll_bar.set)

    #===== ===== Ir buscar o texto a um ficheiro txt
    license_text = """      !!Configuring Virtual Machines in VMware Workstation!!
PLEASE, if you haven't read this message before, read it carefully. The 
file you are executing is a configuration/installation file that will 
automatically configure the hacktux virtual machines in your 
VMware Worksation. This executable is still in a BETA phase, so 
we ask you your understanding in case of problems configuring the 
machines, in addition, if you find any bug please don't hesitate 
to contact the creators of this project, they will be happy to help, 
and to solve any problems.

If the user needs to change the directory where 
vmware workstation is located, or if they need to indicate the 
home directory of the user who is installing hacktux, just click on
the button that has a gear icon with a wrench on it

After reading this, do you still want to configure the machines ?
Authors:
    Duarte Bento Batista - 2211089@my.ipleiria.pt
    Manuel José Antunes Eusébio - 2211049@my.ipleiria.pt

    """
    text_box.config(state=tk.NORMAL)
    text_box.insert(tk.END, license_text)
    text_box.config(state=tk.DISABLED)

    #TODO PERCEBER O QUE ESTA MERDA FAZ
    frame_middle.rowconfigure(0, weight=1)
    frame_middle.columnconfigure(0, weight=1)

    progress_bar = ttk.Progressbar(frame_middle, orient=tk.HORIZONTAL, length=600, mode="determinate")
    progress_bar.grid(columnspan=2)

    #===== Parâmetros da botão cancelar
    frame_button_left = tk.Frame(frame_bottom, width=300, height=50)
    frame_button_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) 

    button_cancel = tk.Button(frame_button_left, text="Cancel", font=("Helvetica", 12, "bold"), command=lambda: exit_application(0))
    button_cancel.pack(fill=tk.BOTH, padx=1, pady=1)

    #===== Parâmetros da botão aceitar
    frame_button_right = tk.Frame(frame_bottom, width=300, height=50)
    frame_button_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    button_accept = tk.Button(frame_button_right, text="Accept", font=("Helvetica", 12, "bold"), command=lambda: start_configuration_vms(text_box, progress_bar, button_accept, root))
    button_accept.pack(fill=tk.BOTH, padx=1, pady=1)

    root.mainloop()


if __name__ == "__main__":
    main()