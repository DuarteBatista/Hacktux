import ctypes
import json
import os
import psutil
import subprocess
import sys
import threading
import time
from cryptography.fernet import Fernet 
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
import vrest


#=====================================================#
#===== Variaveis Globais Utilizadas na Aplicação =====#
#=====================================================#

if getattr(sys, 'frozen', False):
    application_location_base = sys.executable
elif __file__:
    application_location_base = __file__

ERROR_TITLE = "Machine configuration error"
VERSION = "0.2"

thread_list = []
thread_event_list = []

labs_data = {}
virtual_machine_data = {}
conf_settings_data = {}

vmware_directory_path = "C:\\Program Files (x86)\\VMware\\VMware Workstation"
api_rest_executable = "vmrest.exe"
api_cmd_executable = "vmrun.exe"
vmware_executable = "vmware.exe"

cert_path = os.path.dirname(application_location_base) + "\\hacktux-data\\https\\hacktux_cert.crt"
key_path = os.path.dirname(application_location_base) + "\\hacktux-data\\https\\hacktux_private.key"
path_installation_hacktux = os.path.dirname(application_location_base) + "\\installation-hacktux.py"
path_conf_settings = os.path.dirname(application_location_base) + "\\conf-settings.json"
path_vm_json_data = os.path.dirname(application_location_base) + "\\hacktux-data\\virtual-machine-data\\virtual-machines.json"
path_lab_json_data = os.path.dirname(application_location_base) + "\\hacktux-data\\labs-data\\labs.json"
img_path_hacktux = os.path.dirname(application_location_base) + "\\images\\icon-janela-principal-hacktux.png"

#os.path.dirname(os.path.abspath(__file__))
#====================================================================================================#
#==================== Janela de intalação do Hacktux ================================================#
#====================================================================================================#

def open_install_window(parent):
    '''
    Function that opens the hacktux installer
    '''
    global path_installation_hacktux
    try:
        subprocess.run(["python",path_installation_hacktux])
    except Exception as e:
        messagebox.showerror("Cant open installation hacktux",f"Unable to open the window to install hacktux\n{e}",parent=parent)

def start_thread_install_window(parent):
    '''
    Function that creates a thread to execute the function that opens the hacktux installer
    '''
    t1 = threading.Thread(target=open_install_window, args=(parent,))
    t1.daemon=True
    t1.start()

#======================================================================================================================================#
#==================== Função que verifica se as Máquinas virtuais se encontram ligadas ================================================#
#======================================================================================================================================#

def is_vm_on(vm_id):
        '''
        check if vm is on, nedd the workstation id of the vm
        if is on return code 0,
        if is off or other state retun code 1
        if an error occured during executaton return code -1 and the message of the error
        '''
        try:
            response = vrest.get_power(vm_id)
            if response['status'] != 200:
                return {
                    "code" : -1,
                    "message" : response["data"]["message"]
                }
            if response['data']["power_state"] != "poweredOn":
                return {
                    "code" : 1
                }
            return {
                "code" : 0
            }
        except Exception as e:
            return {
                "code" : -1,
                "message" : e
            }

#=========================================================================#
#======== Funções para iniciar os laboratórios ============================#
#=========================================================================#

def start_lab(parent,lab,text_box,start_button,thread_event):
    '''
    Function that starts hacktux labs
    '''
    
    #======================================================#
    #===== Funções auxiliares da função start_lab() =======#
    #======================================================#

    def turn_on_machine(vm):
        '''
        start vm, for argument need the vm that is in lab specified
        if start return code 0,
        if gets an error return code -1
        '''
        try:
            path_api_cmd = f"{vmware_directory_path}\\{api_cmd_executable}"
            vm_user = vm["vm-username"]
            vm_pass = vm["vm-password"]
            vm_path = vm["path"]
            command = f"\"{path_api_cmd}\" -T ws -gu {vm_user} -gp {vm_pass} start \"{vm_path}\" nogui "
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            if result.returncode != 0:
                return {
                    "code" : -1,
                    "message" : result.stdout + " " + result.stderr
                }
            return {
                    "code" : 0,
                }
        except Exception as e:
            return {
                "code" : -1,
                "message" : e
            }

    def turn_off_lab_programs(vm):
        '''
        stop the executation of the programs inside the VMS
        code -1, means that an error ocorrued
        code 0, means that everting work correctly
        '''
        try:
            path_api_cmd = f"{vmware_directory_path}\\{api_cmd_executable}"
            vm_user = vm["vm-username"]
            vm_pass = vm["vm-password"]
            vm_path = vm["path"]
            path_turn_off = vm["scripts_to_run"]["turn-off-lab"]
            command = f"\"{path_api_cmd}\" -T ws -gu {vm_user} -gp {vm_pass} runProgramInGuest \"{vm_path}\" -noWait -activeWindow -interactive \"{path_turn_off}\" "
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            if result.returncode != 0:
                return {
                    "code" : -1,
                    "message" : result.stdout + " " + result.stderr
                }
            return {
                    "code" : 0,
                }
        except Exception as e:
            return {
                "code" : -1,
                "message" : e
            }

    def write_to_log_frame(text_box,message):
        '''
        Function that writes to the lab window what is happening while the lab is running
        '''
        text_box.config(state=tk.NORMAL)
        text_box.insert(tk.END, message)
        text_box.config(state=tk.DISABLED)

    def get_variable_workstation(variable_name,vm):
        '''
        Function used to get data from a vmware workstation variable
        If gets the data return code 0, and for message the data of stdout
        If cant get the data return code -1, and for message return the error
        '''
        try:
            path_api_cmd = f"{vmware_directory_path}\\{api_cmd_executable}"
            vm_user = vm["vm-username"]
            vm_pass = vm["vm-password"]
            vm_path = vm["path"]
            command = f"\"{path_api_cmd}\" -T ws -gu {vm_user} -gp {vm_pass} readVariable \"{vm_path}\" guestVar {variable_name} "
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            if result.returncode != 0:
                return {
                    "code" : -1,
                    "message" : result.stdout + " " + result.stderr
                }
            return {
                    "code" : 0,
                    "message" : result.stdout
                }
        except Exception as e:
            return {
                "code" : -1,
                "message" : e
            }

    def set_variable_workstation(variable_name,variable_data,vm):
        '''
        Function used to set data on a vmware workstation variable
        If sets the data return code 0
        If cant set the data return code -1, and for message return the error
        '''
        try:
            path_api_cmd = f"{vmware_directory_path}\\{api_cmd_executable}"
            vm_user = vm["vm-username"]
            vm_pass = vm["vm-password"]
            vm_path = vm["path"]
            command = f"\"{path_api_cmd}\" -T ws -gu {vm_user} -gp {vm_pass} writeVariable \"{vm_path}\" guestVar {variable_name} {variable_data}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            if result.returncode != 0:
                return {
                    "code" : -1,
                    "message" : result.stdout + " " + result.stderr
                }
            return {
                    "code" : 0,
                }
        except Exception as e:
            return {
                "code" : -1,
                "message" : e
            }

    def decode_message_from_workstation_variable(encode_message):
        '''
        Function used to decode data sent by workstatio variables
        The data placed in the variables must not contain spaces and must not contain quotation marks so that no errors are raised. 
        For this reason, a message structure was created where:
        "_#_" = " "
        "\'" = "\""
        '''
        return encode_message.replace("\'","\"").replace("_#_"," ").replace("\n","")

    def run_script_vm(vm,id_lab,id_vm):
        '''
        Function used to run a batch script on a virtual machine in vmware workstation
        '''
        try:
            path_api_cmd = f"{vmware_directory_path}\\{api_cmd_executable}"
            vm_user = vm["vm-username"]
            vm_pass = vm["vm-password"]
            vm_path = vm["path"]
            vm_script_to_run = vm["scripts_to_run"]["lab-start"]
            command = f"\"{path_api_cmd}\" -T ws -gu {vm_user} -gp {vm_pass} runProgramInGuest \"{vm_path}\" -noWait -activeWindow -interactive \"{vm_script_to_run}\" \"{id_lab}\" \"{id_vm}\""
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            if result.returncode != 0:
                return {
                    "code" : -1,
                    "message" : result.stdout + " " + result.stderr
                }
            return {
                    "code" : 0,
                }
        except Exception as e:
            return {
                "code" : -1,
                "message" : e
            }

    #======================================================#
    #===== Variaveis Globais utilizadas nesta função ======#
    #======================================================#
    global vmware_directory_path
    global api_cmd_executable
    global vmware_executable

    #=================================================================================================#
    #===== Desativar botão start lab, para que não aconteça iniciar duas vezes o start lab ===========#
    #=================================================================================================#
    parent.after(0,lambda start_button=start_button: start_button.config(state=tk.DISABLED))

    #=========================================================================================================================#
    #===== Verifica se o laboratorio contém Máquinas virtuais para executar, caso não tenha apresenta uma mensagem de erro ===#
    #=========================================================================================================================#
    if "vms-necessary" not in lab:
        messagebox.showerror("No vms to execute","This lab dont have vms to execute, for now labs whith no vms dont work",parent=parent)
        parent.after(0,write_to_log_frame,text_box,"This lab dont have vms to execute, for now labs whith no vms dont work\n")
        return

    #=============================================================================#
    #===== Indica na frame dos logs que o laboratório começou a ser iniciado =====#
    #=============================================================================#
    parent.after(0,write_to_log_frame,text_box,lab["name"] + " Starting ...\n")
    
    #=========================================================================================================#
    #===== Verificação se o utilizador parou o laboratorio, é feito desta forma devido ao uso de threads =====#
    #=========================================================================================================#
    if thread_event.is_set():
        return

    #=================================================================================================#
    #===== Verificação se as VMS já se encontram ligadas, ============================================#
    #========== se sim é executado o script de desligar cenários nas VMS =============================#
    #========== se não as VMS são ligadas e os scripts de iniciar os laboratórios são executados =====#
    #=================================================================================================#
    for vm in lab["vms-necessary"]:

        #=========================================================================================================#
        #===== Verificação se o utilizador parou o laboratorio, é feito desta forma devido ao uso de threads =====#
        #=========================================================================================================#
        if thread_event.is_set():
            return
        
        #=====================================================#
        #===== Verifica qual o estado da máquina virtual =====#
        #=====================================================#
        vm_state = is_vm_on(vm["id-workstation"])

        #================================================================================#
        #===== Caso não seja possível obter o estado apresenta uma mensagem de erro =====#
        #================================================================================#
        if vm_state["code"] == -1:
            messagebox.showerror("An error ocurred checking vm state","It was not possible to see "+vm["name"]+" state\n"+vm_state["message"],parent=parent)
            parent.after(0,write_to_log_frame,"It was not possible to see "+vm["name"]+" state\n")
            return
        
        #==========================================================================================================#
        #===== Caso a máquina se encontre desligada, liga a máquina, caso não consiga ligar apresenta um erro =====#
        #==========================================================================================================#
        if vm_state["code"] == 1:
            
            #=========================================================================================================#
            #===== Verificação se o utilizador parou o laboratorio, é feito desta forma devido ao uso de threads =====#
            #=========================================================================================================#
            if thread_event.is_set():
                return

            #==========================================================#
            #===== Ligar a VM, caso não consiga apresenta um erro =====#
            #==========================================================#
            result = turn_on_machine(vm)
            if result["code"] == -1:
                messagebox.showerror("An error ocurred starting vm","It was not possible to start "+vm["name"]+" state\n"+str(result["code"]),parent=parent)
                return
            
            #=================================================================================#
            #===== Se chegar aqui, a VM iniciou com sucesso, é apresentado ao utilizador =====#
            #=================================================================================#
            parent.after(0,write_to_log_frame,text_box,"(*) VM "+vm["name"]+" start with sucess\n")
            continue

        #===============================================================================================================================================================================================#
        #===== Caso a máquina já se encontre ligada, verifica se a mesma contém scripts para serem executados, se sim vai ao script de desligar o cenário, e desliga e verifica se correu tudo bem =====#
        #===============================================================================================================================================================================================#
        if vm_state["code"] == 0:
            
            #=========================================================================================================#
            #===== Verificação se o utilizador parou o laboratorio, é feito desta forma devido ao uso de threads =====#
            #=========================================================================================================#
            if thread_event.is_set():
                return
            

            if "scripts_to_run" in vm:

                #====================================================#
                #===== Executa o script de desligar os cenários =====#
                #====================================================#
                result = turn_off_lab_programs(vm)

                #==================================================================================================================================#
                #===== Variaveis que são utilizadas no ciclo para verificações, vai tentar executar o script se não conseguir espera 1 segundo ====#
                #===== e volta tentar, durante 5 tentativas, se não conseguir em nenhuma dá erro, se conseguir sai do ciclo  ======================#
                #==================================================================================================================================#               
                trys_to_get_values = 0
                max_trys = 5
                flag_exit_cycle = True

                while(flag_exit_cycle):

                    if thread_event.is_set():
                        return
                    
                    if trys_to_get_values == max_trys:
                        messagebox.showerror("An error ocurred stoping programs of vm","It was not possible to stop the programs already running on "+vm["name"]+"\n"+str(result["message"]),parent=parent)
                        parent.after(0,write_to_log_frame,text_box,"(*) It was not possible to stop the programs already running on "+vm["name"]+"\n")
                        return

                    if result["code"] == -1:
                        time.sleep(1)
                        trys_to_get_values = trys_to_get_values + 1
                        result = turn_off_lab_programs(vm)
                        continue

                    if result["code"] == 0:
                        flag_exit_cycle = False

                #===============================================================#
                #===== Vai verificar qual é o estado da execução do script =====#
                #===============================================================#
                variable = "IS_WORKING"
                trys_to_get_values = 0
                max_trys = 10
                flag_exit_cycle = True
                message_before = None
                message = get_variable_workstation(variable,vm)

                while(flag_exit_cycle):

                    #=========================================================================================================#
                    #===== Verificação se o utilizador parou o laboratorio, é feito desta forma devido ao uso de threads =====#
                    #=========================================================================================================#
                    if thread_event.is_set():
                        return
                    
                    #=======================================================================================================#
                    #===== Se o numero de tentativas for igual ao valor máximo de tentavias defenido apresenta um erro =====#
                    #=======================================================================================================#
                    if trys_to_get_values == max_trys:
                        messagebox.showerror("An error ocurred durring executation of the script","After several attempts it was not possible to check the status of the turn-off-lab script on "+vm["name"]+"\n"+str(message["message"]),parent=parent)
                        parent.after(0,write_to_log_frame,text_box,"(*) After several attempts it was not possible to check the status of the turn-off-lab on "+vm["name"]+"\n")
                        return

                    #=========================================================================#
                    #===== Se der algum erro a tentar executar o comando, volta a tentar =====#
                    #=========================================================================#
                    if message["code"] == -1:
                        time.sleep(1)
                        trys_to_get_values = trys_to_get_values + 1
                        message = get_variable_workstation(variable,vm)
                        continue

                    #============================================================================================#
                    #===== Se a mesnagem for igual a null ou \n ou igual à mensagem anterior volta a tentar =====#
                    #============================================================================================#
                    if message["message"] == "null\n" or message["message"] == "\n" or message["message"] == message_before:
                        time.sleep(1)
                        trys_to_get_values = trys_to_get_values + 1
                        message = get_variable_workstation(variable,vm)
                        continue

                    #=========================================================================================================================#
                    #===== Se o valor que vier do comando não for possível converter para json, verifica-se se é null se não for dá erro =====#
                    #=========================================================================================================================#
                    try:
                        execution_result = json.loads(decode_message_from_workstation_variable(message["message"]))
                    except json.decoder.JSONDecodeError:
                        messagebox.showerror("An error ocurred durring executation of the script","The message received by the script could not be converted to json, some error occurred",parent=parent)
                        parent.after(0,write_to_log_frame,text_box,"(*) The message received by the script could not be converted to json, some error occurred\n")
                        return

                    #====================================================================================================================================#
                    #===== Como foi possível obter as mensagens volta-se a colocar a zero o valor das tentativas e a mensagem anterior é atualizada =====#
                    #====================================================================================================================================#
                    trys_to_get_values = 0
                    message_before = message["message"]

                    #==================================================================================================#
                    #===== Caso na mensagem o estado venha a FALSE, quer dizer que deu erro na execução do script =====#
                    #==================================================================================================#
                    if execution_result["state"] == "FALSE":
                        check_command = set_variable_workstation(variable,"null",vm)
                        if check_command["code"] == -1:
                            messagebox.showerror("An error ocurred sending data to workstation variable","It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n"+str(message["message"]),parent=parent)
                            parent.after(0,write_to_log_frame,text_box,"(*) It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n")
                        messagebox.showerror("An error ocurred executing script","An error ocurred during executation of the script:\n"+execution_result["message"],parent=parent)
                        parent.after(0,write_to_log_frame,text_box,"(*) An error ocurred during executation of the script:\n"+execution_result["message"])
                        return
                    
                    #========================================================================================================================================================================================#
                    #===== Se o estado for TRUE quer dizer que algumas das ações feitas no script foram realizadas com sucesso, apresenta a mensagem das ações feitas e continua até receber o finished =====#
                    #========================================================================================================================================================================================#
                    if execution_result["state"] == "TRUE":
                        parent.after(0,write_to_log_frame,text_box,"(*) "+execution_result["message"]+"\n")
                        message = get_variable_workstation(variable,vm)
                        continue

                    #=================================================================================================================================#
                    #===== Se o estado for FINISHED quer dizer que o script foi finalizado com sucesso apresenta a mensagem final e sai do ciclo =====#
                    #=================================================================================================================================#
                    if execution_result["state"] == "FINISHED":

                        #=====================================================================================#
                        #===== Coloca a variavel IS_WORKING a null, para não dar conflitos mais à frente =====#
                        #=====================================================================================#
                        check_command = set_variable_workstation(variable,"null",vm)
                        if check_command["code"] == -1:
                            messagebox.showerror("An error ocurred sending data to workstation variable","It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n"+str(message["message"]),parent=parent)
                            parent.after(0,write_to_log_frame,text_box,"(*) It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n")
                            return
                        
                        parent.after(0,write_to_log_frame,text_box,"(*) "+execution_result["message"]+"\n")
                        flag_exit_cycle = False
                    
    # TODO
    # 1 - Eliminar os dados que estavam na frame
    # 2 - Pedir novamente o estado das VMS
    # 3 - Pedir ao parent que atualize essa secção

    # Requesitos
    # Frame da direita
    # vms do lab

    #==============================================#
    #===== Criar o ID unico deste laboratorio =====#
    #==============================================#

    # Obtém a data e hora atual
    actual_time = time.localtime()

    # Formata a data e hora no formato desejado
    lab_identifier = time.strftime("%Y-%m-%d-%H_%M_%S", actual_time)
    lab_identifier += "-"
    lab_identifier += lab["id"]

    #==========================================================================================================#
    #===== Ciclo que percorre todas as VMs, e incia os scripts necessários para dar inicio ao laboratório =====#
    #==========================================================================================================#
    for vm in lab["vms-necessary"]:

        #=========================================================================================================#
        #===== Verificação se o utilizador parou o laboratorio, é feito desta forma devido ao uso de threads =====#
        #=========================================================================================================#
        if thread_event.is_set():
            return

        #========================================================================#
        #===== Verifica se a vm do laboratorio contem scripts para executar =====#
        #========================================================================#
        if "scripts_to_run" in vm:

            #===========================================================#
            #===== Inicializa a variavel para a execução do script =====#
            #===========================================================#
            variable = "ID_LAB_RUNNING"
            check_command = set_variable_workstation(variable,lab_identifier,vm)
            if check_command["code"] == -1:
                messagebox.showerror("An error ocurred sending data to workstation variable","It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n"+str(check_command["message"]),parent=parent)
                parent.after(0,write_to_log_frame,text_box,"(*) It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n")
                return
            
            #===========================================================#
            #===== Inicializa a variavel para a execução do script =====#
            #===========================================================#
            variable = "ID_VM_RUNNING"
            check_command = set_variable_workstation(variable,vm["id-hacktux"],vm)
            if check_command["code"] == -1:
                messagebox.showerror("An error ocurred sending data to workstation variable","It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n"+str(check_command["message"]),parent=parent)
                parent.after(0,write_to_log_frame,text_box,"(*) It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n")
                return


            parent.after(0,write_to_log_frame,text_box,"(*) Checking if the machines are ready to run the lab,THIS MAY TAKE SOME TIME\n")
            #=================================================================================================================#
            #===== Verificar se a VM se encontra preparada, mais importante quando as VMS estão desligadas e são ligadas =====#
            #=================================================================================================================#
            variable = "IS_VM_READY"
            trys_to_get_values = 0
            max_trys = 90
            flag_exit_cycle = True

            message = get_variable_workstation(variable,vm)

            while(flag_exit_cycle):
                    
                #=========================================================================================================#
                #===== Verificação se o utilizador parou o laboratorio, é feito desta forma devido ao uso de threads =====#
                #=========================================================================================================#
                if thread_event.is_set():
                    return

                #=======================================================================================================#
                #===== Se o numero de tentativas for igual ao valor máximo de tentavias defenido apresenta um erro =====#
                #=======================================================================================================#
                if trys_to_get_values == max_trys:
                    messagebox.showerror("An error ocurred checking if vm is ready","After several attempts it was not possible to check if "+vm["name"]+" is ready\n",parent=parent)
                    parent.after(0,write_to_log_frame,text_box,"(*) After several attempts it was not possible to check if "+vm["name"]+" is ready\n")
                    return
                
                #===========================================================================#
                #===== Se der algum erro a tentar executar o comando volta-se a tentar =====#
                #===========================================================================#
                if message["code"] == -1 or (message["code"] == 0 and message["message"] =="\n"):
                    time.sleep(1)
                    trys_to_get_values = trys_to_get_values + 1
                    message = get_variable_workstation(variable,vm)
                    continue

                #=============================================================================================================================================#
                #===== Se for possível executar e a varivel vier com o valor a TRUE, sai-se do ciclo, espera-se 15 segundos quando a VM acaba de iniciar =====#
                #=============================================================================================================================================#
                if message["code"] == 0 and message["message"] =="TRUE\n":
                    if trys_to_get_values != 0:
                        time.sleep(15)
                    parent.after(0,write_to_log_frame,text_box,"(*) VM "+vm["name"]+" is ready\n")
                    flag_exit_cycle = False

            #===============================================================================================#
            #===== Inicio da execução do script necessário para colocar em funcionamento o laboratório =====#
            #===============================================================================================#
            trys_to_get_values = 0
            max_trys = 5
            flag_exit_cycle = True
            result = run_script_vm(vm,lab_identifier,vm["id-hacktux"])

            while(flag_exit_cycle):

                if thread_event.is_set():
                    return
                
                if trys_to_get_values == max_trys:
                    messagebox.showerror("An error ocurred sending signal to vm to start lab","It was not possible to send the signal to "+vm["name"]+" to start lab "+lab["name"]+"\n"+str(result["message"]),parent=parent)
                    parent.after(0,write_to_log_frame,text_box,"(*) It was not possible to send the signal to "+vm["name"]+" to start lab "+lab["name"]+"\n")
                    return

                if result["code"] == -1:
                    time.sleep(1)
                    trys_to_get_values = trys_to_get_values + 1
                    result = run_script_vm(vm,lab_identifier,vm["id-hacktux"])
                    continue

                if result["code"] == 0:
                    flag_exit_cycle = False

            #===============================================================#
            #===== Vai verificar qual é o estado da execução do script =====#
            #===============================================================#
            variable = "IS_WORKING"
            trys_to_get_values = 0
            max_trys = 90
            flag_exit_cycle = True
            message_before = None
            message = get_variable_workstation(variable,vm)

            while(flag_exit_cycle):

                #=========================================================================================================#
                #===== Verificação se o utilizador parou o laboratorio, é feito desta forma devido ao uso de threads =====#
                #=========================================================================================================# 
                if thread_event.is_set():
                    return
                
                #=======================================================================================================#
                #===== Se o numero de tentativas for igual ao valor máximo de tentavias defenido apresenta um erro =====#
                #=======================================================================================================#
                if trys_to_get_values == max_trys:
                    messagebox.showerror("An error ocurred durring executation of the script","After several attempts it was not possible to check the status of the turn-off-lab script on "+vm["name"]+"\n"+str(message["message"]),parent=parent)
                    parent.after(0,write_to_log_frame,text_box,"(*) After several attempts it was not possible to check the status of the turn-off-lab on "+vm["name"]+"\n")
                    return

                #===================================================================================#
                #===== Se der algum erro a tentar executar o comando volta a tentar executá-lo =====#
                #===================================================================================#
                if message["code"] == -1:
                    time.sleep(1)
                    trys_to_get_values = trys_to_get_values + 1
                    message = get_variable_workstation(variable,vm)
                    continue

                #==================================================================================================================#
                #===== Se a mensagem que vier pelo comando for null ou for \n ou for igual à mensagem anterior volta a tentar =====#
                #==================================================================================================================#
                if message["message"] == "null\n" or message["message"] == "\n" or message["message"] == message_before:
                    time.sleep(1)
                    trys_to_get_values = trys_to_get_values + 1
                    message = get_variable_workstation(variable,vm)
                    continue

                #===================================================================================================================================#
                #===== Se o valor que vier do comando não for possível converter para json, quer dizer que algum erro ocorreu apresenta o erro =====#
                #===================================================================================================================================#
                try:
                    execution_result = json.loads(decode_message_from_workstation_variable(message["message"]))
                except json.decoder.JSONDecodeError:
                    messagebox.showerror("An error ocurred durring executation of the script","The message received by the script could not be converted to json, some error occurred",parent=parent)
                    parent.after(0,write_to_log_frame,text_box,"(*) The message received by the script could not be converted to json, some error occurred\n")
                    return

                #===================================================================================================================================================#
                #===== Como foi possível obter as mensagens volta-se a colocar a zero o valor das tentativas e a message_before fica a ser a mensagem que veio =====#
                #===================================================================================================================================================#
                trys_to_get_values = 0
                message_before = message["message"]

                #==================================================================================================#
                #===== Caso na mensagem o estado venha a FALSE, quer dizer que deu erro na execução do script =====#
                #==================================================================================================#
                if execution_result["state"] == "FALSE":
                    check_command = set_variable_workstation(variable,"null",vm)
                    if check_command["code"] == -1:
                        messagebox.showerror("An error ocurred sending data to workstation variable","It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n"+str(message["message"]),parent=parent)
                        parent.after(0,write_to_log_frame,text_box,"(*) It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n")
                    messagebox.showerror("An error ocurred executing script","An error ocurred during executation of the script:\n"+execution_result["message"],parent=parent)
                    parent.after(0,write_to_log_frame,text_box,"(*) An error ocurred during executation of the script:\n"+execution_result["message"])
                    return
                
                #=============================================================================================================================================================#
                #===== Se o estado for TRUE quer dizer que algumas das ações feitas no script foram realizadas com sucesso, apresenta a mensagem e volta a pedir o valor =====#
                #=============================================================================================================================================================#
                if execution_result["state"] == "TRUE":
                    parent.after(0,write_to_log_frame,text_box,"(*) "+execution_result["message"]+"\n")
                    message = get_variable_workstation(variable,vm)
                    continue

                #============================================================================================================================================================================================#
                #===== Se o estado for FINISHED quer dizer que o script foi finalizado com sucesso apresenta a mensagem final e sai do ciclo, coloca a variavel a null para não dar erros mais à frente =====#
                #============================================================================================================================================================================================#
                if execution_result["state"] == "FINISHED":
                    check_command = set_variable_workstation(variable,"null",vm)
                    if check_command["code"] == -1:
                        messagebox.showerror("An error ocurred sending data to workstation variable","It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n"+str(message["message"]),parent=parent)
                        parent.after(0,write_to_log_frame,text_box,"(*) It was not possible to send data for variable "+variable+" on "+vm["name"]+"\n")
                        return
                    parent.after(0,write_to_log_frame,text_box,"(*) "+execution_result["message"]+"\n")
                    flag_exit_cycle = False

    #=========================================================================================================#
    #===== Verificação se o utilizador parou o laboratorio, é feito desta forma devido ao uso de threads =====#
    #=========================================================================================================# 
    if thread_event.is_set():
        return

    #==========================================================================================================================================================#
    #===== Verificar se o vmware gui já se encontra a ser executado no sistema, se não se encontra manda executar uma thread que vai iniciar o vmware gui =====#
    #==========================================================================================================================================================#
    flag_vmware_workstation_running = False
    for proc in psutil.process_iter(attrs=['name']):
        if proc.info['name'] == vmware_executable:
            flag_vmware_workstation_running = True
            break

    if not flag_vmware_workstation_running:
        parent.after(0,thread_start_vmware_workstation,parent)    

    #=======================================================================================================#
    #==== Se chegar aqui quer dizer que está tudo okay e pode apresentar que o laboratório está pronto =====#
    #=======================================================================================================#
    messagebox.showinfo("Lab working with sucess",f"It was possible to get the laboratory "+lab["name"]+" up and running",parent=parent)
    parent.after(0,write_to_log_frame,text_box,f"(*) It was possible to get the laboratory "+lab["name"]+" up and running\n")

def thread_start_lab(parent,lab,text_box,start_button):
    '''
    Function to start thread, that starts the specified LAB
    '''
    global thread_list
    global thread_event_list
    
    thread_event = threading.Event()
    thread = threading.Thread(target=start_lab, args=(parent,lab,text_box,start_button,thread_event))
    thread.daemon= True

    thread_list.clear()
    thread_event_list.clear()

    thread_list.append(thread)
    thread_event_list.append(thread_event)
    
    thread.start()

#==============================================================================================================#
#======== Funções para desligar o laboratorio  =================================================================#
#==============================================================================================================#
def exit_lab(lab,turn_off_button,start_button,parent):
    '''
    Funtion that exit the lab, its prepare to exit the lab if is not yet ready
    '''

    def turn_off_vms(vm):
        '''
        turn off vm, for argument need the vm that is in lab specified
        if start return code 0,
        if gets an error return code -1
        '''
        try:
            path_api_cmd = f"{vmware_directory_path}\\{api_cmd_executable}"
            vm_user = vm["vm-username"]
            vm_pass = vm["vm-password"]
            vm_path = vm["path"]
            command = f"\"{path_api_cmd}\" -T ws -gu {vm_user} -gp {vm_pass} stop \"{vm_path}\" soft "
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            if result.returncode != 0:
                return {
                    "code" : -1,
                    "message" : result.stdout + " " + result.stderr
                }
            return {
                    "code" : 0,
                }
        except Exception as e:
            return {
                "code" : -1,
                "message" : e
            }

    #==================================================#
    #===== Variaveis globais utilizadas na função =====#
    #==================================================#
    global vmware_directory_path
    global api_cmd_executable
    global thread_event_list
    global img_path_hacktux

    #=======================================================================================#
    #===== Pergunta ao utilizador se este têm a certeza que pretende sair da aplicação =====#
    #=======================================================================================#
    response = messagebox.askquestion("Leave The Lab","Are you sure you want to leave the lab ?",parent=parent)
    if response == "no":
        return

    #==============================================================================================================================================================================#
    #===== Verifica se existe alguma evento de thread na lista se sim ativa o evento, isto acontece para caso estaja a ser iniciado um lab ele pare quando este set for feito =====#
    #==============================================================================================================================================================================#
    if len(thread_event_list) != 0:
        for event in thread_event_list:
            event.set()

    #==================================================================================================================#
    #===== Desativa os botões de start lab e turn-off-lab para que não ocorram conflitos na execução da aplicação =====#
    #==================================================================================================================#
    parent.after(0,lambda start_button=start_button: start_button.config(state=tk.DISABLED))
    parent.after(0,lambda turn_off_button=turn_off_button: turn_off_button.config(state=tk.DISABLED))

    #==============================================================================================================================================#
    #===== Vai verifica neste laboratorio quais são as VMS que estão ligadas, as que estiveram são adicionadas ao array para serem desligadas =====#
    #==============================================================================================================================================#
    array_vms_on = []
    for vm in lab["vms-necessary"]:
        
        #========================================#
        #===== Verifica qual o estado da VM =====#
        #========================================# 
        vm_state = is_vm_on(vm["id-workstation"])

        #================================================================#
        #===== Se der erro ao obter o estado da VM apresenta o erro =====#
        #================================================================#
        if vm_state["code"] == -1:
            messagebox.showerror("An error ocurred checking vm state","It was not possible to see "+vm["name"]+" state\n"+str(vm_state["message"]),parent=parent)
            return
        
        #=================================================================================================#
        #===== Se a VM se encontrar ligada, esta é adicionada ao array para de seguida ser desligada =====#
        #=================================================================================================#
        if vm_state["code"] == 0:
            array_vms_on.append(vm)
    
    #===========================================================================================#
    #===== Se o array estiver não estiver vazio isso indica que existem VMS para desligar  =====#
    #===========================================================================================#
    if len(array_vms_on) != 0:

        #===================================================================================================================#
        #===== Pergunta ao utilizador se ele pretende desligar as VMs ao sair do lab ou pretende deixar as VMs ligadas =====#
        #===================================================================================================================#
        response = messagebox.askquestion("Turn off VMs","There are virtual machines in this lab that are power up, do you want to turn off the virtual machines ?",parent=parent)
        if response == "no":
            parent.after(0,lambda:parent.destroy())
            return
        
        #=============================================================================================================#
        #===== Parametrização da janela que vai apresentar ao utilizador quais VMs se encontram a ser desligadas =====#
        #=============================================================================================================#
        state_shutdown_window = tk.Toplevel(parent)
        state_shutdown_window.title("Shutting down virtual machines!")
        state_shutdown_window.geometry("400x80")
        imageHacktux = tk.PhotoImage(file=img_path_hacktux)
        state_shutdown_window.iconphoto(False, imageHacktux)
        state_shutdown_window.resizable(False, False)
        state_shutdown_window.grab_set()
        
        #============================================================================================================================#
        #===== Percorre o array das VMs e desliga cada uma, a janela é dinâmica pois apresenta quais vms estão a ser desligadas =====#
        #============================================================================================================================#
        for vm in array_vms_on:

            delete_items_frame(state_shutdown_window)
            label_state_vms = tk.Label(state_shutdown_window, text="Shutting down " + vm["name"] + " ...", wraplength=380, justify="center")
            label_state_vms.pack(pady=20, padx=20)
            state_shutdown_window.update_idletasks()

            check_command = turn_off_vms(vm)
            if check_command["code"] == -1:
                messagebox.showerror("An error ocurred checking vm state","It was not possible to see "+vm["name"]+" state\n"+check_command["message"],parent=parent)
                return
            
        #=============================================================================================#
        #===== Apresentao ao utilizador uma mensagem a indicar que todas as VMs foram desligadas =====#
        #=============================================================================================#
        messagebox.showinfo("VMs Shutdown","All VMs in this lab have been shut down",parent=parent)
        
    #=================================================================#
    #===== Destrói a janela que estava a apresentar as mensagens =====#
    #=================================================================#
    parent.after(0,lambda:parent.destroy())

        
def thread_exit_lab(lab,turn_off_button,start_button,parent):
    '''
    Function that start thread, that start exit_lab function
    '''
    global thread_list
    thread = threading.Thread(target=exit_lab,args=(lab,turn_off_button,start_button,parent))
    thread.daemon= True

    thread_list.clear()
    thread_list.append(thread)

    thread.start()

#==============================================================================================================#
#======== Funções para iniciar o VMware Workstation após os laboratorios iniciarem  ============================#
#==============================================================================================================#
def start_vmware_workstation(parent):
    '''
    Fuction that start the VMware Workstation GUI, the objective is after starting the labs start the GUI 
    for iteraction with the user
    '''
    global vmware_directory_path
    global vmware_executable
    try:
        command = f"{vmware_directory_path}\\{vmware_executable}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        if result.returncode != 0:
            messagebox.showerror("Unable to start vmware workstation","Unable to start vmware workstation\n"+result.stderr,parent=parent)
            return
        return
    except Exception as e:
        messagebox.showerror("Unable to start vmware workstation","Unable to start vmware workstation\n"+e,parent=parent)
        return

def thread_start_vmware_workstation(parent):
    '''
    Function that start thread, that start start_vmware_workstation function
    '''
    global thread_list
    thread = threading.Thread(target=start_vmware_workstation,args=(parent,))
    thread.daemon= True

    thread_list.clear()
    thread_list.append(thread)

    thread.start()

#====================================================================================================#
#===== Janela detalhada dos laboratórios ============================================================#
#====================================================================================================# 
def open_labs_window(parent, lab, imageHacktux):
    '''
    Function that show in detail an specif lab of hacktux
    '''

    def closing_window():
        '''
        Function use for binding event of delete window
        '''
        thread_exit_lab(lab,button2,button1,modal_window)

    #=================================================#
    #===== Variaveis Globais usadas nesta função =====#
    #=================================================#
    global virtual_machine_data

    #==========================================================#
    #===== Janela para apresentar a página do laboratório =====#
    #==========================================================#   
    modal_window = tk.Toplevel(parent)
    modal_window.title(lab["name"])
    modal_window.geometry("1280x720")
    modal_window.resizable(False, False)
    modal_window.iconphoto(False,imageHacktux)
    modal_window.protocol("WM_DELETE_WINDOW", closing_window)
    modal_window.grab_set()

    #================================================================================================#
    #===== Adiciona à janela o loading screen pois pode demorar algum tempo a carregar a página =====#
    #================================================================================================#  
    imageLabel = tk.Label(modal_window, image=imageHacktux)
    imageLabel.pack(fill=tk.BOTH,anchor=tk.CENTER)

    loading_label = tk.Label(modal_window, text="Loading...", font=("Helvetica", 24, "bold"))
    loading_label.pack(fill=tk.BOTH,anchor=tk.CENTER)
    
    modal_window.update_idletasks()

    delete_items_frame(modal_window)

    #=================================================================#
    #===== Variaveis que vao guardar o nome e a descrição do lab =====#
    #=================================================================#
    lab_name = lab['name']
    lab_description = lab['description']
    
    #=======================================================================#
    #===== Configuração do grid para distribuir uniformemente o espaço =====#
    #=======================================================================#
    for i in range(2):  # Duas colunas
        modal_window.grid_columnconfigure(i, weight=1, uniform="equal")
    for j in range(3):  # Três linhas
        if j == 0:
            modal_window.grid_rowconfigure(j, weight=0)  # Peso menor para a primeira linha
        else:
            modal_window.grid_rowconfigure(j, weight=1, uniform="equal")

    #===============================================#
    #===== Adiciona o título na primeira linha =====#
    #===============================================#
    label_laboratory = tk.Label(modal_window, text=lab_name, font=("Helvetica", 24, "bold"))
    label_laboratory.grid(row=0, column=0, columnspan=2, pady=(20, 10), sticky="nsew")

    #===================================#
    #===== Frame superior esquerdo =====#
    #===================================#
    frame_top_left = tk.Frame(modal_window,highlightbackground="black", highlightthickness=2)
    frame_top_left.grid(row=1, column=0, sticky="nsew")
    nameLab = tk.Label(frame_top_left, text=lab_name, font=("Helvetica", 16, "bold"))
    nameLab.grid(row=0, column=0, sticky="w")
    descriptionLab = tk.Label(frame_top_left, text=lab_description, font=("Helvetica", 10), wraplength=600, justify="left")
    descriptionLab.grid(row=1, column=0, padx=10, pady=10, sticky="w")

    #==================================#
    #===== Frame Superior direito =====#
    #==================================#
    frame_top_right = tk.Frame(modal_window,highlightbackground="black", highlightthickness=2)
    frame_top_right.grid(row=1, column=1, sticky="nsew")
    name_LabelRight = tk.Label(frame_top_right, text="Virtual Machine Status", font=("Helvetica", 16, "bold"))
    name_LabelRight.grid(row=0, column=1, sticky="w")
    
    #===================================================================================================================================================================#
    #===== Verificação do estado das VMS, caso alguma não tenha sido possível obter o estado apresenta um erro, caso não existam VMs aparece que o lab não têm VMs =====#
    #===================================================================================================================================================================#
    flag_show_error_vm_not_config = False
    flag_show_error_vm_without_state = False
    if "vms-necessary" in lab:
        for i,vm in enumerate(lab["vms-necessary"]):

            #===========================================================#
            #===== Verificar se a VM está no virtual-machines.json =====#
            #===========================================================#
            flag_vm_configured = False
            flag_state_vm = True
            for item in virtual_machine_data["vms"]:
                if item["id-hacktux"] == vm["id-hacktux"] and item["id-workstation"] == vm["id-workstation"]:
                    flag_vm_configured = True
                    break

            #==========================================================================================================================================================================#
            #===== Se existir alguma VM do Lab que não estiver configurada, é ativada a flag para apresentar o erro geral,e é colocado na janela que essa vm não está configurada =====#
            #==========================================================================================================================================================================#
            if not flag_vm_configured:
                flag_show_error_vm_not_config = True
                machine_status = tk.Label(frame_top_right, text=vm["name"] + " - Not configured", font=("Helvetica", 10), wraplength=600, justify="left")
                machine_status.grid(row=i+1, column=1, padx=5, pady=20,sticky="w")
                continue
            
            #========================================================================================================#
            #===== Vai tentar ir buscar o estado da VM, se não for possível obter o estado ativa a flag de erro =====#
            #========================================================================================================#
            try:
                power_vm = vrest.get_power(vm["id-workstation"])
                if power_vm["status"] != 200:
                    flag_state_vm = False
            except Exception as e:
                flag_state_vm = False
            
            #===========================================================================================================================#
            #===== Se não for possível obter o estado apresenta, na janela que não conseguio obter o estado e ativa a flag de erro =====#
            #===========================================================================================================================#
            if not flag_state_vm:
                flag_show_error_vm_without_state = True
                machine_status = tk.Label(frame_top_right, text=vm["name"] + " - The status is unknown", font=("Helvetica", 10), wraplength=600, justify="left")
                machine_status.grid(row=i+1, column=1, padx=5, pady=20,sticky="w")
                continue
    
            #===================================================================================================================#
            #===== Se a VM estiver configurada e for possível obter o estado é apresentado na janela qual é o estado da VM =====#
            #===================================================================================================================#
            machine_status = tk.Label(frame_top_right, text=vm["name"] + " - " + power_vm['data']["power_state"], font=("Helvetica", 10), wraplength=600, justify="left")
            machine_status.grid(row=i+1, column=1, padx=5, pady=20,sticky="w")
    
    else:
        machine_status = tk.Label(frame_top_right, text="There are no VMs to start up in this lab", font=("Helvetica", 10), wraplength=600, justify="left")
        machine_status.grid(row=1, column=1, padx=5, pady=20,sticky="w")

    #===================================#
    #===== Frame inferior esquerdo =====#
    #===================================#
    frame_bottom_left = tk.Frame(modal_window, highlightbackground="black", highlightthickness=2)
    frame_bottom_left.grid(row=2, column=0, sticky="nsew")

    Nome_logs = tk.Label(frame_bottom_left, text="Logs", font=("Helvetica", 16, "bold"))
    Nome_logs.grid(row=2, column=0, sticky="w")

    left_logs = tk.Text(frame_bottom_left, wrap=tk.WORD, state=tk.NORMAL, width=75, height=17)
    left_logs.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10,0))
    left_logs.config(state=tk.DISABLED)

    #==================================#
    #===== Frame inferior direito =====#
    #==================================#
    frame_bottom_right = tk.Frame(modal_window, highlightbackground="black", highlightthickness=2)
    frame_bottom_right.grid(row=2, column=1, sticky="nsew")

    #============================================#
    #===== Botões na frame inferior direita =====#
    #============================================#
    button1 = tk.Button(frame_bottom_right, text="Start Lab", font=("Helvetica", 14), width=15, height=2, command= lambda: thread_start_lab(modal_window,lab,left_logs,button1))
    button1.grid(row=0, column=0, padx=10, pady=10)

    button2 = tk.Button(frame_bottom_right, text="Exit Lab", font=("Helvetica", 14), width=15, height=2, command= lambda: thread_exit_lab(lab,button2,button1,modal_window))
    button2.grid(row=1, column=0, padx=10, pady=10)

    #==========================================================================================#
    #===== Flags que se estiverem a TRUE, apresentam os erros que ocorreram anteriormente =====#
    #==========================================================================================#
    if flag_show_error_vm_not_config:
        messagebox.showwarning("Vms not configured","There are vms in this lab that are not yet configured, so the lab can't run. Check the status of the machines to see which vms are not configured.",parent=modal_window)
        button1.config(state=tk.DISABLED)
        button2.config(state=tk.DISABLED)

    if flag_show_error_vm_without_state:
        messagebox.showwarning("vms without status","There are vms in this lab that dont give the status, so the lab can't run. Check the status of the machines to see which vms dont have status",parent=modal_window)
        button1.config(state=tk.DISABLED)
        button2.config(state=tk.DISABLED)

    #=======================================================================================#
    #===== Atualiza a frame modal window e faz com que o parent espere por esta janela =====#
    #=======================================================================================#
    modal_window.update_idletasks()
    parent.wait_window(modal_window)

#====================================================================================================#
#===== Mostra o catálogo de laboratórios ============================================================#
#====================================================================================================# 
def catalog(parent, imageHacktux, canvas_catalog,scroll_bar):
    '''
    Function that load the catalog on the frame 
    '''

    #=================================================#
    #===== Variaveis Globais usadas nesta função =====#
    #=================================================#
    global labs_data

    #===================================================================#
    #===== Limpa a área direita antes de adicionar novos elementos =====#
    #===================================================================#
    delete_items_frame(parent)

    #=============================================================================#
    #===== Inicio da criação da frame que vai receber os labs para o catalogo=====#
    #=============================================================================#
    frame_title = tk.Frame(parent, width=960,bg = "white" )
    frame_title.pack(fill=tk.X, expand=True)
    frame_Labs = tk.Frame(parent, width=960, bg = "white")
    frame_Labs.pack(fill=tk.X, expand=True)

    #========================================#
    #===== Adiciona o título "Catálogo" =====#
    #========================================#
    label_catalog = tk.Label(frame_title, text="Catalog", font=("Helvetica", 32, "bold"), bg = "white")
    label_catalog.pack(fill=tk.X,expand=True,pady=(20, 10))
    

    #=================================================================================#
    #===== Percorre a lista dos laboratórios e aprsenta-os na janela do catálogo =====#
    #=================================================================================#
    for lab in labs_data['labs']:  
        lab_name = lab['name']
        lab_description = lab['description']

        button_frame = tk.Frame(frame_Labs, bg="white", width=960, height=150)
        button_frame.pack(fill=tk.X, padx=10, pady=10, expand=True)
        
        button = tk.Button(button_frame, image=imageHacktux, bd=0, highlightthickness=0, width=150, height=220, command=lambda parent=parent,lab=lab,imageHacktux=imageHacktux: open_labs_window(parent,lab,imageHacktux))
        button.grid(row=0, column=0, rowspan=2, sticky="w", padx=10)

        text_frame = tk.Frame(button_frame, bg="white")
        text_frame.grid(row=0, column=1, sticky="nw")

        label = tk.Label(text_frame, text=lab_name, font=("Helvetica", 16), bg="white", anchor="w")
        label.pack(anchor="w")

        description = tk.Label(text_frame, text=lab_description, font=("Helvetica", 10), bg="white", wraplength=850, justify="left")
        description.pack(anchor="w",pady=15, expand=True, fill=tk.BOTH)

    #================================================================#
    #===== Manda a frame atualizar para mostrar os laboratórios =====#
    #================================================================#
    parent.update_idletasks()
    canvas_catalog.configure(scrollregion=canvas_catalog.bbox("all"))
    canvas_catalog.configure(yscrollcommand=scroll_bar.set)

#====================================================================================================#
#===== Função para apagar todos os dados da janela do lado direito=====#
#====================================================================================================# 
def delete_items_frame(frame):
    '''
    Function that delete all items inside an frame
    '''
    for item in frame.winfo_children():
        item.destroy()
#====================================================================================================#
#===== Função para escolher a diretoria do vmware =====#
#====================================================================================================# 
def choose_folder(folder_entry):
        folder = filedialog.askdirectory()
        if folder:
            folder_entry.delete(0, tk.END)
            folder_entry.insert(0, folder)
#====================================================================================================#
#===== Função para guardar as pastas escolhidas anteriormente =====#
#====================================================================================================# 
def save_configuration(folder_entry,folder_entry2,root):
    '''
    Function that save the directory of vmware workstation and home directory in conf-settings.json
    '''
    #=================================================#
    #===== Variaveis Globais usadas nesta função =====#
    #=================================================#
    global path_conf_settings
    global conf_settings_data

    #=============================================================================================#
    #===== Pergunta ao utilizador se este têm mesmo a certeza que quer salvar a configuração =====#
    #=============================================================================================#
    response = messagebox.askquestion("Save Configuration?", "Are you sure you want to save the configuration?", parent=root)
    if response == "no":
        return
    
    #=========================================================================#
    #===== Guarda nesta variaveis os caminhos escolhidos pelo utilizador =====#
    #=========================================================================#
    new_vmware_path = folder_entry.get()
    new_home_path = folder_entry2.get()

    #=============================================================================================#
    #===== Verifica se existe o ficheiro conf-settings se não existir ele é criado novamente =====#
    #=============================================================================================#
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

    #==================================================================================================#
    #===== Altera a diretoria do vmware e do home user para a diretoria escolhida pelo utilizador =====#
    #==================================================================================================#
    configuration["vmware_directory_path"] = new_vmware_path
    configuration["user_home_directory_path"] = new_home_path

    #==============================================================#
    #===== Salva a configuração de volta para o ficheiro JSON =====#
    #==============================================================#
    with open(path_conf_settings, 'w',encoding="utf-8") as file:
        json.dump(configuration, file, indent=4)

    #===================================================#
    #===== Carrega os novos dados para a aplicação =====#
    #===================================================#
    conf_settings_data = configuration

    #=============================================#
    #===== Apresenta uma mensagem de sucesso =====#
    #=============================================#
    messagebox.showinfo("Success!", "The configuration has been saved successfully!", parent=root)

#====================================================================================================#
#===== Janela de ajustes das configurações ==========================================================#
#====================================================================================================# 
def settings_ajustments(frame,root):
    '''
    Function that show in hacktux an windows with the configurations that user can do
    '''
    #======================================================================#
    #===== Elimina os dados da frame direita para colocar esta janela =====#
    #======================================================================#
    delete_items_frame(frame)
    
    #====================================================================#
    #===== Variavel que guarda a fonte usada pelas labels da janela =====#
    #====================================================================#
    font_style = ("Helvetica", 12)

    #========================================#
    #===== Frame superior para o título =====#
    #========================================#
    frame_title = tk.Frame(frame, width=960, bg="white")
    frame_title.pack(fill=tk.X, expand=True)

    #=========================================#
    #===== Frame para escolha das opções =====#
    #=========================================#
    frame_settings = tk.Frame(frame, bg="grey85")
    frame_settings.pack(fill=tk.BOTH, expand=True)

    #==================#
    #===== TÍTULO =====#
    #==================#
    label_title = tk.Label(frame_title, text="Settings", font=("Helvetica", 26, "bold"), bg="white")
    label_title.pack(fill=tk.X, expand=True, pady=(20, 10))

    #================================#
    #===== Frame para os botões =====#
    #================================#
    buttons_frame = tk.Frame(frame_title, bg="white")
    buttons_frame.pack(fill=tk.X, padx=10, pady=10)

    #======================================================#
    #===== Botão para iniciar o Instalador do Hacktux =====#
    #======================================================#
    button_install = tk.Button(buttons_frame, text="Hacktux installation", width=50, height=2, command= lambda: start_thread_install_window(root))
    button_install.pack(side=tk.TOP,expand=True)

    main_frame = tk.Frame(frame_settings, padx=20, pady=50, bg="grey85", highlightthickness=2, highlightbackground="black")
    main_frame.pack(fill=tk.BOTH,expand=True)

    #========================================#
    #===== Label que indica a instrução =====#
    #========================================#
    folder_label = tk.Label(main_frame, text="Choose the VMware directory:", font=font_style)
    folder_label.pack() 

    #===========================================================#
    #===== Caixa de texto para mostrar o caminho escolhido =====#
    #===========================================================#
    folder_entry = tk.Entry(main_frame, width=50, font=font_style)
    folder_entry.pack(pady=5)

    #==================================================================#
    #===== Botão para abrir o dialgo de escolher pasta no windows =====#
    #==================================================================#
    choose_button = tk.Button(main_frame, text="Choose folder", font=font_style, command=lambda: choose_folder(folder_entry))
    choose_button.pack(pady=10)

    #========================================#
    #===== Label que indica a instrução =====#
    #========================================#
    home_folder_label = tk.Label(main_frame, text="Choose the user's home directory:", font=font_style)
    home_folder_label.pack() 

    #===========================================================#
    #===== Caixa de texto para mostrar o caminho escolhido =====#
    #===========================================================#
    folder_entry2 = tk.Entry(main_frame, width=50, font=font_style)
    folder_entry2.pack(pady=5)

    #==================================================================#
    #===== Botão para abrir o dialgo de escolher pasta no windows =====#
    #==================================================================#
    choose_button2 = tk.Button(main_frame, text="Choose folder", font=font_style, command=lambda: choose_folder(folder_entry2))
    choose_button2.pack(pady=10)

    #==============================================#
    #===== Botão para salvar as configurações =====#
    #==============================================#
    save_button = tk.Button(main_frame, text="Save settings", font=font_style, command=lambda: save_configuration(folder_entry,folder_entry2,root))
    save_button.pack(pady=20)

#==============================================================================================#
#===== Janela para apresentar as VMs ==========================================================#
#==============================================================================================# 
def virtual_machine_window(frame,canvas_catalog,frame_internal,scroll_bar,imageHacktux): 
    '''
    Function that show virtual machine window
    '''
    #==============================================================================================#
    #===== Alterar os parâmetros das máquinas, como colocá-las em modos de requisitos minimos =====#
    #==============================================================================================#  
    def edit_characteristics(frame,vm_restrictions_data,vm_data_json):
        def edit_chracteristics_window(frame,vm_restrictions_data,vm_data_json):
        
            def update_requirements():
                try:
                    new_value_memory = memory_entry.get()
                    new_value_cpu= cpu_entry.get()
                    update_vm = vrest.update_vm(vm_data_json["id-workstation"], {"memory": int(new_value_memory), "processors": int(new_value_cpu)})
                    #Verificar se a atualização foi feita com sucesso
                    if update_vm['status'] != 200:
                        messagebox.showerror("Update VM error","Unable to update " + vm_data_json["name"] + "\n" + update_vm['data']['Message'], parent=edit_characteristics_window)
                        return
                    else:
                        #Mensagem de sucesso e atualização dos valores das caracterisiticas das maquinas
                        messagebox.showinfo("Success Update", vm_data_json["name"] + " updated with sucess \nProcessors: " + new_value_cpu + "\nMemory: " + new_value_memory, parent=edit_characteristics_window)
                        virtual_machine_window(frame,canvas_catalog,frame_internal,scroll_bar,imageHacktux)
                except Exception as e:
                    messagebox.showerror("Update VM error","Unable to update " + vm_data_json["name"] + "\n" + str(e), parent=edit_characteristics_window)

            def set_minimum_requirements(vm_data_json):
                #MessageBox para confirmar a alteração das caracteristicas
                res = messagebox.askquestion("Change VM Settings to minimum","Do you really want to change "+vm_data_json["name"]+" vm settings to minimum?  \n\nNumember of processors: "+vm_data_json['requirements']['minimum']["number-processors"]+"\nRAM memory: "+ vm_data_json['requirements']['minimum']["RAM-memory"],parent=edit_characteristics_window)
                if res == "no":
                    return
                
                try:
                    minimum_cpu = vm_data_json['requirements']['minimum']["number-processors"]
                    minimum_ram = vm_data_json['requirements']['minimum']["RAM-memory"]
                    update_vm = vrest.update_vm(vm_data_json["id-workstation"], {"memory": int(minimum_ram), "processors": int(minimum_cpu)})
                    #Verificar se a atualização foi feita com sucesso
                    if update_vm['status'] != 200:
                        messagebox.showerror("Update VM error","Unable to update " + vm_data_json["name"] + "\n" + update_vm['data']['Message'], parent=edit_characteristics_window)
                        return
                    else:
                        #Mensagem de sucesso e atualização para os valores mínimos
                        messagebox.showinfo("Success Update", vm_data_json["name"] + " updated with sucess \nProcessors: " + minimum_cpu + "\nMemory: " + minimum_ram, parent=edit_characteristics_window)        
                        virtual_machine_window(frame,canvas_catalog,frame_internal,scroll_bar,imageHacktux)
                except Exception as e:
                    messagebox.showerror("Update VM error","Unable to update " + vm_data_json["name"] + "\n" + str(e), parent=edit_characteristics_window)

                        
            def revert_vm_to_default(vm_data_json, parent):

                global vmware_directory_path
                global api_cmd_executable

                # Verificar se a máquina virtual está configurada no ficheiro json
                vmx_path = vm_data_json["path"]
                vm_snapshots = vm_data_json["snapshot"]
                try:
                    #listar os snapshots disponíveis, fiz isto mais para verificar se havia erros, por exemplo alguma máquina não ter snapshots
                    list_snapshots_command = f"\"{vmware_directory_path}\\{api_cmd_executable}\" listSnapshots \"{vmx_path}\""
                    list_snapshots_result = subprocess.run(list_snapshots_command, shell=True, capture_output=True, text=True, check=True)

                    if list_snapshots_result.returncode != 0:
                        messagebox.showerror("Listing snapshots went wrong", f"It was not possible to list the snapshots of "+item['name']+"\n"+list_snapshots_result.stderr+".", parent=frame)
                        return

                    if "Total snapshots: 0" in list_snapshots_result.stdout or "Total snapshots" not in list_snapshots_result.stdout:
                        messagebox.showerror("Snapshot Error", f"There are no snapshots for "+vm_data_json['name']+".", parent=frame)
                        return

                    # Verificar se o snapshot default proveniente do ficheiro json está na lista
                    if vm_snapshots not in list_snapshots_result.stdout:
                        messagebox.showerror("Snapshot Error", f"Snapshot {vm_snapshots} not found for "+vm_data_json['name']+".", parent=frame)
                        return
                    
                    revert_command = f"\"{vmware_directory_path}\\{api_cmd_executable}\" revertToSnapshot \"{vmx_path}\" \"{vm_snapshots}\""
                    revert_result = subprocess.run(revert_command, shell=True, capture_output=True, text=True, check=True)
                    #Tratar os erros da execução do comando
                    if revert_result.returncode != 0:
                        messagebox.showerror("Revert Error", f"Failed to revert " + vm_data_json['name'] + " to snapshot.", parent=frame)
                        return

                except Exception as e:
                    messagebox.showerror("Revert Error", f"An error occurred while reverting {vm_data_json['name']} to snapshot. ", parent=frame)
                    return

                
                messagebox.showinfo("Revert Success", f"It was possible to revert {vm_data_json['name']} to their original state", parent=frame)

                virtual_machine_window(frame, canvas_catalog, frame_internal, scroll_bar, imageHacktux)        
                    
                    

            global img_path_hacktux
            #Janela com as caracteristicas da máquina
            edit_characteristics_window = tk.Toplevel(frame)
            edit_characteristics_window.title("Machine Settings " + vm_data_json["name"])
            edit_characteristics_window.geometry("600x400")
            imageHacktux = tk.PhotoImage(file=img_path_hacktux)
            edit_characteristics_window.iconphoto(False, imageHacktux)
            edit_characteristics_window.resizable(False, False)

            title_frame = tk.Frame(edit_characteristics_window)
            title_frame.pack(pady=20)

            content_frame = tk.Frame(edit_characteristics_window)
            content_frame.pack(pady=10, padx=20, fill="x")
            #Nome da maquina
            label_characteristics = tk.Label(title_frame, text=vm_data_json["name"], font=("Helvetica", 16, "bold"))
            label_characteristics.pack()

            label_name = tk.Label(content_frame, text=f"VM:", anchor="w", font=("Helvetica", 12, "bold"))
            label_name.pack(anchor="w", pady=5)
            label_name_2 = tk.Label(content_frame, text=vm_data_json["name"], anchor="w", font=("Helvetica", 12))
            label_name_2.pack(anchor="w", pady=5)
            #Mostrar o id da maquina
            id_frame = tk.Frame(content_frame)
            id_frame.pack(anchor="w", pady=5, fill="x")
            label_id = tk.Label(id_frame, text=f"ID:", anchor="w", font=("Helvetica", 12, "bold"))
            label_id.pack(side="left")
            label_id_2 = tk.Label(id_frame, text=f"{vm_restrictions_data['data']['id']}", anchor="w", font=("Helvetica", 12))
            label_id_2.pack(side="left")
            #Mostrar o numero de CPUs da maquina
            cpu_frame = tk.Frame(content_frame)
            cpu_frame.pack(anchor="w", pady=5, fill="x")
            label_cpu = tk.Label(cpu_frame, text="CPU Processors:", anchor="w", font=("Helvetica", 12, "bold"))
            label_cpu.pack(side="left")
            cpu_entry = tk.Entry(cpu_frame)
            cpu_entry.insert(0, vm_restrictions_data['data']['cpu']['processors'])
            cpu_entry.pack(side="left")
            #Mostrar a memoria da maquina
            memory_frame = tk.Frame(content_frame)
            memory_frame.pack(anchor="w", pady=5, fill="x")
            label_memory = tk.Label(memory_frame, text="Memory (MB):", anchor="w", font=("Helvetica", 12, "bold"))
            label_memory.pack(side="left")
            memory_entry = tk.Entry(memory_frame)
            memory_entry.insert(0, vm_restrictions_data['data']['memory'])
            memory_entry.pack(side="left")

            # Add a frame for the buttons at the bottom of the window
            buttons_frame = tk.Frame(edit_characteristics_window)
            buttons_frame.pack(side="bottom", fill="x", pady=10, padx=20)

            # Add "Alterar para requisitos minimos" button on the bottom left
            button_min_req = tk.Button(buttons_frame, text="Change to minimum requirements", command= lambda:set_minimum_requirements(vm_data_json))
            button_min_req.pack(side="left")
            
            # Add "Revert VM to Default" 
            button_revert_default = tk.Button(buttons_frame, text="Revert VM to Default", command=lambda vm_data_json=vm_data_json: revert_vm_to_default(vm_data_json, frame))
            button_revert_default.pack(side="left", padx=10) 


            # Add a single "Save" button on the bottom right
            button_save = tk.Button(buttons_frame, text="Save", command=lambda: (update_requirements(), edit_characteristics_window.destroy()))
            button_save.pack(side="right")
        
        #Mensagem de aviso para quem não percebe no que ta a mexer
        def show_warning_modal(frame,conf_settings_data):
            
            #Mensagem de continuar a editar voltando a apresentar a mensagem de aviso
            def continue_editing():
                modal_window.grab_release()
                modal_window.destroy()
                edit_chracteristics_window(frame,vm_restrictions_data,vm_data_json)
            
            #Mensagem de continuar a editar não voltando a apresentar a mensagem de aviso
            def continue_and_dont_show():
                global path_conf_settings
                conf_settings_data['error_message'] = "false"
                with open(path_conf_settings, "w") as file:
                    json.dump(conf_settings_data, file, indent=4)
                continue_editing()
            
            #Cancelar a edição
            def cancel_editing():
                modal_window.grab_release()
                modal_window.destroy()
            
            #janela que mostra a mensagem de aviso
            global img_path_hacktux
            modal_window = tk.Toplevel(frame)
            modal_window.title("Warning!")
            modal_window.geometry("500x200")
            imageHacktux = tk.PhotoImage(file=img_path_hacktux)
            modal_window.iconphoto(False, imageHacktux)
            modal_window.resizable(False, False)
            modal_window.grab_set()  # Make the window modal
            #mensagem de aviso
            warning_label = tk.Label(modal_window, text="Using edit mode without knowledge of the values that can be set in the machine settings can cause poor performance of the virtual machines and the computer itself, in extreme cases the machines can be damaged and the computer can stop working. If you are not aware of the settings you can set, do not edit the machines, click on 'Cancel'.", wraplength=380, justify="center")
            warning_label.pack(pady=20, padx=20)
            #botões para continuar a editar, continuar a editar sem mostrar a mensagem de aviso e cancelar a edição
            button_frame = tk.Frame(modal_window)
            button_frame.pack(pady=20)

            continue_button = tk.Button(button_frame, text="Continue", command=continue_editing)
            continue_button.pack(side=tk.LEFT, padx=10)

            dont_show_button = tk.Button(button_frame, text="Continue and don't show this message again", command=continue_and_dont_show)
            dont_show_button.pack(side=tk.LEFT, padx=10)

            cancel_button = tk.Button(button_frame, text="Cancel", command=cancel_editing)
            cancel_button.pack(side=tk.LEFT, padx=10)
        
        #Mostrar a mensagem de aviso apenas se a tag estiver a true
        global conf_settings_data
        if conf_settings_data["error_message"] == "true":
            show_warning_modal(frame, conf_settings_data)
        else:
            edit_chracteristics_window(frame,vm_restrictions_data,vm_data_json)
                  
    #================================================================#
    #===== Mostrar todos os dados relevantes da maquinas ==#
    #================================================================#      
    def show_characteristics(parent,vm_restrictions_data,vm_status,vm_data_json):
        global img_path_hacktux
        characteristics_window = tk.Toplevel(parent)
        characteristics_window.title("Machine Specs - " + vm_data_json["name"])
        characteristics_window.geometry("700x400")
        imageHacktux = tk.PhotoImage(file=img_path_hacktux)
        characteristics_window.iconphoto(False, imageHacktux)
        characteristics_window.resizable(False, False)
        
        # Frame for the title
        title_frame = tk.Frame(characteristics_window)
        title_frame.pack(pady=20)

        # Frame for the main content
        content_frame = tk.Frame(characteristics_window)
        content_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Title
        label_characteristics = tk.Label(title_frame, text=vm_data_json["name"], font=("Helvetica", 16, "bold"))
        label_characteristics.pack()


        label_name = tk.Label(content_frame, text=f"VM: " + vm_data_json["name"], anchor="w", font=("Helvetica", 12))
        label_name.pack(anchor="w", pady=5)
        # ID
        label_id = tk.Label(content_frame, text=f"ID: {vm_restrictions_data['data']['id']}", anchor="w", font=("Helvetica", 12))
        label_id.pack(anchor="w", pady=5)

        # CPU Processors
        label_cpu = tk.Label(content_frame, text=f"CPU Processors: {vm_restrictions_data['data']['cpu']['processors']}", anchor="w", font=("Helvetica", 12))
        label_cpu.pack(anchor="w", pady=5)
        
        #Status
        label_status = tk.Label(content_frame, text=f"Status: {vm_status['data']['power_state']}", anchor="w", font=("Helvetica", 12))
        label_status.pack(anchor="w", pady=5)
        
        # Memory
        label_memory = tk.Label(content_frame, text=f"Memory (MB): {vm_restrictions_data['data']['memory']}", anchor="w", font=("Helvetica", 12))
        label_memory.pack(anchor="w", pady=5)
        
        # NICs
        label_nics_title = tk.Label(content_frame, text="NIC List:", anchor="w", font=("Helvetica", 12, "bold"))
        label_nics_title.pack(anchor="w", pady=10)

        for nic in vm_restrictions_data["data"]['nicList']['nics']:
            nic_frame = tk.Frame(content_frame)
            nic_frame.pack(anchor="w", padx=20, pady=5, fill="x")

            label_nic_index = tk.Label(nic_frame, text=f"Index: {nic['index']}", anchor="w", font=("Helvetica", 12))
            label_nic_index.grid(row=0, column=0, sticky="w")
            
            label_nic_type = tk.Label(nic_frame, text=f"Type: {nic['type']}", anchor="w", font=("Helvetica", 12))
            label_nic_type.grid(row=0, column=1, padx=10, sticky="w")
            
            label_nic_vmnet = tk.Label(nic_frame, text=f"VMNet: {nic['vmnet']}", anchor="w", font=("Helvetica", 12))
            label_nic_vmnet.grid(row=0, column=2, padx=10, sticky="w")
            
            label_nic_mac = tk.Label(nic_frame, text=f"MAC Address: {nic['macAddress']}", anchor="w", font=("Helvetica", 12))
            label_nic_mac.grid(row=0, column=3, padx=10, sticky="w")

        if vm_status['data']['power_state'] == "poweredOn":
            vm_ip = vrest.get_ip(vm_data_json["id-workstation"])
            label_ip = tk.Label(content_frame, text=f"IP Address: {vm_ip['data']['ip']}", anchor="w", font=("Helvetica", 12))
            label_ip.pack(anchor="w", pady=5)

    #================================================================#
    #===== Definir todas as máquinas para os requisitos mínimos =====#
    #================================================================#
    def all_Vms_To_Minimum():

        #===========================#
        #===== Variavel Global =====#
        #===========================#
        global virtual_machine_data

        #=========================================================#
        #===== Variavel para verificar se ocorreu algum erro =====#
        #=========================================================#
        flag_error = False
        
        #====================================================================#
        #===== Verificação se as máquinas encontram-se todas desligadas =====#
        #====================================================================#
        for item in virtual_machine_data["vms"]:
            power_status = vrest.get_power(item["id-workstation"])
            if power_status['data']['power_state'] == "poweredOn":
                messagebox.showerror("Error change the minimum requirements",item["name"] + " is on, turn it off so you can change the minimum requirements",parent=frame)
                return
        
        #========================================================================================================#
        #===== Alteração dos Requesitos Minimos das máquinas, caso ocorra algum erro, o mesmo é apresentado =====#
        #========================================================================================================#
        for item in virtual_machine_data["vms"]:
            cpu_minimum = item["requirements"]["minimum"]["number-processors"]
            ram_minimun = item["requirements"]["minimum"]["RAM-memory"]
            minimum_requirements = vrest.update_vm(item["id-workstation"], {'processors':int(cpu_minimum), "memory":int(ram_minimun)})

            if minimum_requirements['status'] != 200:
                messagebox.showerror("Error change the minimum requirements", minimum_requirements['data']['Message'] + " (" + item["name"] + ")",parent=frame)
                flag_error = True
                break
                
        if not flag_error:
            messagebox.showinfo("Success", "All machines have been changed to the minimum requirements",parent=frame)

        #===========================================================================================#
        #===== Volta-se a carregar a janela das Máquinas Virtuais para atualizar as alterações =====#
        #===========================================================================================#      
        virtual_machine_window(frame,canvas_catalog,frame_internal,scroll_bar,imageHacktux)

    
    #=======================================#
    #===== Codigo dos snapshots gerais =====#
    #=======================================#  
    def all_Vms_To_Default():

        #======================================================#
        #===== Variaveis Globais utilizadas nesta função ======#
        #======================================================#
        global virtual_machine_data
        global vmware_directory_path
        global api_cmd_executable

        #===========================================================================================================================================#
        #===== Ciclo for que vai listar os snapshots que estão na VM e vai verificar se existe o Snapshot base caso exista é feita a reversão ======#
        #===========================================================================================================================================#
        flag_revert_vm = True
        for item in virtual_machine_data["vms"]:
            vmx_path = item["path"]
            vm_snapshots = item["snapshot"]
            try:
                #listar os snapshots disponíveis, fiz isto mais para verificar se havia erros, por exemplo alguma máquina não ter snapshots
                list_snapshots_command = f"\"{vmware_directory_path}\\{api_cmd_executable}\" listSnapshots \"{vmx_path}\""
                list_snapshots_result = subprocess.run(list_snapshots_command, shell=True, capture_output=True, text=True, check=True)
                
                if list_snapshots_result.returncode != 0:
                    messagebox.showerror("Listing snapshots went wrong", f"It was not possible to list the snapshots of "+item['name']+"\n"+list_snapshots_result.stderr+".", parent=frame)
                    flag_revert_vm = False
                    break

                if "Total snapshots: 0" in list_snapshots_result.stdout or "Total snapshots" not in list_snapshots_result.stdout:
                    messagebox.showerror("Snapshot Error", f"There are no snapshots for "+item['name']+".", parent=frame)
                    flag_revert_vm = False
                    break

                # Verificar se o snapshot default proveniente do ficheiro json está na lista
                if vm_snapshots not in list_snapshots_result.stdout:
                    messagebox.showerror("Snapshot Error", f"Snapshot {vm_snapshots} not found for "+item['name']+".", parent=frame)
                    flag_revert_vm = False
                    break

                # Reverter para o snapshot default
                revert_command = f"\"{vmware_directory_path}\\{api_cmd_executable}\" revertToSnapshot \"{vmx_path}\" \"{vm_snapshots}\""
                revert_result = subprocess.run(revert_command, shell=True, capture_output=True, text=True, check=True)
                #Tratar os erros da execução do comando
                if revert_result.returncode != 0:
                    messagebox.showerror("Revert Error", f"Failed to revert " + item['name'] + " to snapshot.", parent=frame)
                    flag_revert_vm = False
                    break

            except Exception as e:
                messagebox.showerror("Revert Error", f"An error occurred while reverting {item['name']} to snapshot. ", parent=frame)
                flag_revert_vm = False
                break

        if flag_revert_vm:
            messagebox.showinfo("Revert Success", "It was possible to revert all the machines to their original state", parent=frame)

        #=============================================================================#
        #===== Atualizar a janela de máquinas virtuais para refletir as mudanças =====#
        #=============================================================================#
        virtual_machine_window(frame, canvas_catalog, frame_internal, scroll_bar, imageHacktux)
        
    #================================================================#
    #===== Codigo principal do menu das VMs ==#
    #================================================================#  

    #=================================================#
    #===== Variaveis Globais usadas nesta função =====#
    #=================================================#
    global conf_settings_data
    global virtual_machine_data
    global labs_data

    #================================================================================#
    #===== Apresenta a frame de loading, pois para carregar as VMS pode demorar =====#
    #================================================================================#
    delete_items_frame(frame)
    loading_screen(frame_internal, imageHacktux, canvas_catalog,scroll_bar)
    delete_items_frame(frame)

    #===================================================================#
    #===== Criação da Janela que vai apresentar as VMs e os botões =====#
    #===================================================================#
    title_frame = tk.Frame(frame, width=960)
    buttons_frame = tk.Frame(frame, width=960)
    virtual_machines_frame = tk.Frame(frame, width=960)

    title_frame.pack(fill=tk.X,expand=True)
    buttons_frame.pack(fill=tk.X,expand=True,pady=(0,20))
    virtual_machines_frame.pack(fill=tk.X,expand=True)

    vm_window_title = tk.Label(title_frame,text="Virtual Machines", font=("Helvetica", 32, "bold"))
    vm_window_title.pack(fill=tk.X,pady=(0,15))
    
    button_minimum_requirements = tk.Button(buttons_frame, text="Change specs of all machines to Minimum Requirements",font=("Helvetica", 12, "bold"), command=all_Vms_To_Minimum)
    button_minimum_requirements.pack(side=tk.RIGHT,expand=True)
 
    button_revert_snapshot = tk.Button(buttons_frame, text="Revert machines to their original state",font=("Helvetica", 12, "bold"), command=all_Vms_To_Default)
    button_revert_snapshot.pack(side=tk.RIGHT,expand=True)

    flag_show_error_vms = False
    for item in virtual_machine_data["vms"]:
        flag_unable_get_specs_vm = False
        #===== Pedido à API que vai buscar os dados restritos das máquinas
        try:
            vm_restrictions_data = vrest.get_vm_restrictions(item["id-workstation"])
            if vm_restrictions_data["status"] != 200:
                flag_unable_get_specs_vm = True
        except Exception as e:
            flag_unable_get_specs_vm = True
        
        #===== Pedido à API que vai buscar o estado das máquinas
        try:
            vm_state = vrest.get_power(item["id-workstation"])
            if vm_state["status"] != 200:
                flag_unable_get_specs_vm = True
        except Exception as e:
            flag_unable_get_specs_vm = True
    
        if flag_unable_get_specs_vm:
            # ===== Indica que vai ser apresentado um erro a indicar que não foi possível obter os dados das vms
            flag_show_error_vms = True

            #===== Criação da frame para colocar as VMS
            vm_frame = tk.Frame(virtual_machines_frame, width=800)
            vm_frame.pack(fill=tk.X,expand=True,pady=(0,15))

            #===== Criação Frame para colocar o Titulo da Máquina,as carcteristicas e os botões
            vm_name_frame = tk.Frame(vm_frame, width=225)
            vm_characteristics_frame = tk.Frame(vm_frame, width=450)
            vm_buttons_frame = tk.Frame(vm_frame, width=225)

            
            vm_name_frame.pack(side=tk.LEFT)
            vm_characteristics_frame.pack(side=tk.LEFT,fill=tk.X,expand=True)
            vm_buttons_frame.pack(side=tk.RIGHT)

            #===== Criação dos dados a serem lá colocados
            #===== Nome da Maquina
            label_vm_name = tk.Label(vm_name_frame, text=item["name"] + " - Specs is unknown", font=("Helvetica", 16, "bold"))
            label_vm_name.pack(fill=tk.X,expand=True)
            continue

        
        separator = tk.Frame(virtual_machines_frame, height=2, bg="black")
        separator.pack(fill='x', pady=(10, 25))

        #===== Criação da frame para colocar as VMS
        vm_frame = tk.Frame(virtual_machines_frame, width=100)
        vm_frame.pack(fill=tk.X, expand=True,pady=(0,15))

        #===== Criação Frame para colocar o Titulo da Máquina,as carcteristicas e os botões
        vm_name_frame = tk.Frame(vm_frame, width=110)
        vm_characteristics_frame = tk.Frame(vm_frame, width=450)
        vm_buttons_frame = tk.Frame(vm_frame, width=215)

        
        vm_name_frame.pack(side=tk.LEFT, fill=tk.X)
        vm_characteristics_frame.pack(side=tk.LEFT,fill=tk.X,expand=True)
        vm_buttons_frame.pack(side=tk.RIGHT)

        #===== Criação dos dados a serem lá colocados
        #===== Nome da Maquina
        label_vm_name = tk.Label(vm_name_frame, text=item["name"], font=("Helvetica", 16, "bold"))
        label_vm_name.pack(fill=tk.X,expand=True)

        #=====Mostrar as Carcteristicas da máquina
        
        label_vm_processors = tk.Label(vm_characteristics_frame, text="Number of Processors: " + str(vm_restrictions_data["data"]["cpu"]["processors"]), font=("Helvetica", 8, "bold"))
        label_vm_ram_memory = tk.Label(vm_characteristics_frame, text="RAM memory: " + str(vm_restrictions_data["data"]["memory"]), font=("Helvetica", 8, "bold"))
        
        lable_vm_state = tk.Label(vm_characteristics_frame, text="Machine Status: " + str(vm_state["data"]["power_state"]), font=("Helvetica", 8, "bold"))

        label_vm_processors.pack(side=tk.TOP,anchor=tk.W)
        label_vm_ram_memory.pack(side=tk.TOP,anchor=tk.W)
        lable_vm_state.pack(side=tk.TOP,anchor=tk.W)

        #===== Botões visualizar e editar carcteristicas da máquina
        button_vm_show = tk.Button(vm_buttons_frame, text="Show",font=("Helvetica", 8, "bold"), command=lambda frame=frame,vm_restrictions_data=vm_restrictions_data,vm_status=vm_state,vm_data_json=item : show_characteristics(frame,vm_restrictions_data,vm_status,vm_data_json))
        button_vm_edit = tk.Button(vm_buttons_frame, text="Edit",font=("Helvetica", 8, "bold" ),command=lambda frame=frame,vm_restrictions_data=vm_restrictions_data,vm_data_json=item: edit_characteristics(frame,vm_restrictions_data,vm_data_json))

        button_vm_show.pack(side=tk.TOP,fill=tk.BOTH,padx=25,pady=1)
        button_vm_edit.pack(side=tk.TOP,fill=tk.BOTH,padx=25,pady=1)
        separator = tk.Frame(virtual_machines_frame, height=2, bg="black")
        #separator.pack(fill='x', pady=(10, 10))
        separator.pack(fill='x', pady=(10, 25))

    if flag_show_error_vms:
        messagebox.showwarning("can't get vms data","Data could not be obtained from some VMs.")

    # Fim - Atualizar a frame e o canvas para voltar à base
    frame_internal.update_idletasks()
    canvas_catalog.configure(scrollregion=canvas_catalog.bbox("all"))
    canvas_catalog.configure(yscrollcommand=scroll_bar.set)
#====================================================================================================#
#===== Janela de carregamento enquanto obtem os dados das maquinas virtuais =====#
#====================================================================================================# 
def loading_screen(frame_internal, imageHacktux, canvas_catalog,scroll_bar):
    imageLabel = tk.Label(frame_internal, image=imageHacktux)
    imageLabel.pack(expand=True,anchor=tk.CENTER)

    loading_label = tk.Label(frame_internal, text="Loading...", font=("Helvetica", 24, "bold"))
    loading_label.pack(expand=True,anchor=tk.CENTER)

    frame_internal.update_idletasks()
    canvas_catalog.configure(scrollregion=canvas_catalog.bbox("all"))
    canvas_catalog.configure(yscrollcommand=scroll_bar.set)
#====================================================================================================#
#===== Função para carrega<r os dados dos ficheiros para a nossa aplicação=====#
#====================================================================================================# 
def load_file_to_app(path, file_name):
    try:   
        with open(path, "r", encoding="utf-8") as file:
            data_file = json.load(file)
        return data_file
    except FileNotFoundError:
        return {
            "error": f"The file {file_name} was not found, in the directory of the program"
        }
    except json.JSONDecodeError:
        return {
            "error": f"The file {file_name} is not in JSON format"
        }
    except Exception as e:
        return {    
            "error": f"Error opening the file {file_name}: {e}"
        }
#====================================================================================================#
#===== Carregar para a app o ficheeiro virtual-machines.json=====#
#====================================================================================================# 
def load_virtual_machines_data(path, file_name):
    global virtual_machine_data
    virtual_machine_data = load_file_to_app(path,file_name)
    
#====================================================================================================#
#===== Carregar para a app o ficheeiro labs.json =====#
#====================================================================================================#     
def load_labs_data(path, file_name):
    global labs_data
    labs_data = load_file_to_app(path,file_name)

#====================================================================================================#
#===== Carregar para a app o ficheiro conf-settings.json =====#
#====================================================================================================#        
def load_conf_settings_data(path, file_name):
    global conf_settings_data
    conf_settings_data = load_file_to_app(path,file_name)

#====================================================================================================#
#===== função prinipal do código =====#
#====================================================================================================#   


def main():

    global VERSION
    global labs_data
    global virtual_machine_data
    global conf_settings_data
    global path_lab_json_data
    global path_vm_json_data
    global path_conf_settings
    global img_path_hacktux
    global vmware_directory_path
    global api_rest_executable
    global cert_path
    global key_path

    #====================================================================================================#
    #===== Atualiza o código da scrollbar =====#
    #====================================================================================================#   
    def on_frame_configure(canvas):
        # Atualiza a região de scroll do canvas para cobrir o novo conteúdo
        bbox = canvas.bbox("all")
        if bbox:
            # Calcula a altura da frame e a altura do canvas
            frame_height = bbox[3]
            canvas_height = canvas.winfo_height()
            if frame_height <= canvas_height:
                # Desativa a rolagem se o conteúdo cabe no canvas
                canvas.configure(scrollregion=(0, 0, bbox[2], canvas_height))
            else:
                # Ativa a rolagem se o conteúdo não cabe no canvas
                canvas.configure(scrollregion=(0, 0, bbox[2], bbox[3]))
    
    #====================================================================================================#
    #===== codigo que permite que a aplicação nao se desformate ao ser movida =====#
    #====================================================================================================#   
    def resize_frame(event, canvas, frame,frame_id):
        # Ajusta a largura do frame para a largura do canvas
        canvas_width = canvas.winfo_width()
        frame_width = frame.winfo_reqwidth()
        if frame_width < canvas_width:
            canvas.itemconfig(frame_id, width=canvas_width)
        else:
            canvas.itemconfig(frame_id, width=frame_width)

    #====================================================================================================#
    #===== Codigo da janela principal =====#
    #====================================================================================================#            

    # ===== Criação das threads que vão buscar os ficheiros para a aplicação
    t1 = threading.Thread(target=load_virtual_machines_data, args=(path_vm_json_data, "virtual-machines.json"))
    t1.daemon=True

    t2 = threading.Thread(target=load_labs_data, args=(path_lab_json_data, "labs.json"))
    t2.daemon=True

    t3 = threading.Thread(target=load_conf_settings_data, args=(path_conf_settings, "conf-settings.json"))
    t3.daemon=True
    
    # ===== Incio das threads que vão buscar os dados da aplicação
    t1.start()
    t2.start()
    t3.start()
    
    # ===== Espera o termino da função e caso tenha dado erro termina a aplicação
    t1.join()
    if "error" in virtual_machine_data:
        messagebox.showerror("Load File Error", "Error:"+virtual_machine_data['error'])
        sys.exit(1)

    # ===== Espera o termino da função e caso tenha dado erro termina a aplicação
    t2.join()
    if "error" in labs_data:
        messagebox.showerror("Load File Error", "Error:"+labs_data['error'])
        sys.exit(1)
   
    # ===== Espera o termino da função e caso tenha dado erro termina a aplicação
    t3.join()
    if "error" in conf_settings_data:
        messagebox.showerror("Load File Error", "Error:"+conf_settings_data['error'])
        sys.exit(1)     

    # ================================================== #
    # ===== Ligar o VMREST na aplicação ============= #
    # ================================================== #

    #===== Tentar encontrar a diretoria do VMware Workstation, começa por ver a diretoria default do VMware
    #===== Verifica se a diretoria existe no sistema, se existir avança, se não vai verificar ao ficheiro conf-settings
    if not os.path.exists(vmware_directory_path):
        vmware_directory_path = conf_settings_data['vmware_directory_path']

        #===== Verifica se a diretoria que está no ficheiro conf-settings existe no sistema, se existir avança, se não apresenta um erro
        if not os.path.exists(vmware_directory_path):
            messagebox.showerror("Vmware directory not found", "Could not find the VMware Workstation directory")
            sys.exit(1)  

    #===== Tentar encontrar o executável da API do VMware Workstation
    executable_path = os.path.join(vmware_directory_path, api_rest_executable)
    executable_components ="-c \"" + cert_path+ "\" -k \"" + key_path + "\""
    #===== Caso não exista o executável na diretoria é apresentado uma mensagem de erro
    if not os.path.exists(executable_path):
        messagebox.showerror("REST API not found", "The VMware Workstation REST API executable could not be found")
        sys.exit(1) 

    #===== Vai verificar se a API REST do VMware já se encontra a correr
    process_running_flag = False
    for proc in psutil.process_iter(attrs=['name']):
        if proc.info['name'] == api_rest_executable:
            process_running_flag = True
            break

    #===== Se não estiver a correr executa com privilegios de administrador o executável vmrest.exe
    if not process_running_flag:
        
        try:
            #===== Executa uma funcção do windows em C que permite executar aplicações com provilegios de Admin
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable_path, executable_components, None, 0)

            #===== Verificar qual foi o resultado da Função
            if ret == 5:
                messagebox.showerror("REST API not running", "To configure the machines, you must allow \'vmrest\' to run with administrator privileges")
                sys.exit(1) 
            
            elif ret < 32:
                messagebox.showerror("REST API not running", "Unable to run the VMware Workstation REST API executable")
                sys.exit(1)

        except Exception as e:
            messagebox.showerror("REST API not running", "Unable to run the VMware Workstation REST API executable")
            sys.exit(1)

    # ================================================== #
    # ===== Autentica no VM REST ======================= #
    # ================================================== #

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
            messagebox.showerror("Unable to autheticate REST API", "Unable to authenticate to VMware Workstation REST API, maximum attempts exceeded")
            sys.exit(1)

        auth_attempts += 1
        time.sleep(1)
        status=vrest.authenticate(rest_api_username, rest_api_password)

    
    #===== Criação do da Página Principal
    root = tk.Tk()
    #===== Parâmetros da Página Principal
    root.title(f"Hacktux - Version: {VERSION} ")
    root.geometry("1280x720")
    #===== Coloca como icon a imagem do Hacktux
    imageHacktux = tk.PhotoImage(file=img_path_hacktux)
    root.iconphoto(False, imageHacktux)

    # Divisao da Janela em 2 (LEFT = 25%; RIGHT = 75%)
    frame_left = tk.Frame(root, width=320)
    frame_right = tk.Frame(root, width=960, bg="white")

    frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
    frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Divisao da janela da esquerda em 3 (Imagem Hacktux = 25%, Nome aplicação mais versão= 25%, Botões= 50%)
    frame_left_top = tk.Frame(frame_left, width=320, height=180)
    frame_left_middle = tk.Frame(frame_left, width=320, height=180)
    frame_left_bottom = tk.Frame(frame_left, width=320, height=360)

    frame_left_top.pack(side=tk.TOP, fill=tk.BOTH, expand=False)
    frame_left_middle.pack(fill=tk.BOTH, expand=False)
    frame_left_bottom.pack(fill=tk.BOTH, expand=True)

    # Imagem para a frame do TOPO
    imageLabel = tk.Label(frame_left_top, image=imageHacktux)
    imageLabel.pack(fill=tk.BOTH)


    # Nome da Aplicação e Versão para o meio
    label_name_app = tk.Label(frame_left_middle, text="Hacktux", font=("Helvetica", 32, "bold"))
    label_name_app.pack()
    label_version = tk.Label(frame_left_middle, text=f"OT CyberRange Platform, Version: {VERSION}", font=("Helvetica", 10, "bold"))
    label_version.pack(pady=(0, 15))
    separator = ttk.Separator(frame_left_middle, orient='horizontal')
    separator.pack(fill='x', pady=(10, 10))

    # Botoes a colocar na aplicação
    button1 = tk.Button(frame_left_bottom, text="Catalog", font=("Helvetica", 12, "bold"), bd=1, highlightthickness=0, command=lambda: catalog(frame_internal, imageHacktux, canvas_catalog,scroll_bar))
    button1.pack(fill=tk.BOTH, padx=1, pady=(5, 1), expand=True)

    button3 = tk.Button(frame_left_bottom, text="Virtual Machines", font=("Helvetica", 12, "bold"), command= lambda: virtual_machine_window(frame_internal,canvas_catalog,frame_internal,scroll_bar,imageHacktux))
    button3.pack(fill=tk.BOTH, padx=1, pady=1, expand=True)

    button5 = tk.Button(frame_left_bottom, text="Settings", font=("Helvetica", 12, "bold"), command= lambda: settings_ajustments(frame_internal,root))
    button5.pack(fill=tk.BOTH, padx=1, pady=1, expand=True)

    tk.Label(frame_left_bottom, text=f"Application developed by:", font=("Helvetica", 10, "bold")).pack()
    tk.Label(frame_left_bottom, text=f"Duarte Bento Batista", font=("Helvetica", 10, "bold")).pack()
    tk.Label(frame_left_bottom, text=f"Manuel José Antunes Eusébio", font=("Helvetica", 10, "bold")).pack()

    #===== Janela do Lado Direito Catálogo Primeira a ser carregada
    #===== Criação de um canvas (a razão para isso deve-se a ser um elemento possivel de adptar com um scroll bar)
    canvas_catalog = tk.Canvas(frame_right, bg = "white")
    canvas_catalog.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)

    #===== Criação do scroll bar
    scroll_bar = tk.Scrollbar(frame_right, orient=tk.VERTICAL, command=canvas_catalog.yview)
    scroll_bar.pack(side=tk.RIGHT,fill=tk.BOTH)

    #===== Configurações a fazer no canvas para sincornizar e colocar a funciona o scrool bar
    canvas_catalog.configure(yscrollcommand=scroll_bar.set)
    #===== ===== Faz com que quando o canvas é configurado ele reconfigura-se novamente
    canvas_catalog.bind('<Configure>', lambda e: canvas_catalog.configure(scrollregion=canvas_catalog.bbox("all")))
    #===== ===== Faz com que caso o rato seja mexido quando este está no canvas que este acione o yscroll
    canvas_catalog.bind("<Enter>", lambda event:canvas_catalog.bind_all("<MouseWheel>", lambda e: canvas_catalog.yview_scroll(-1 * int(e.delta / 120), "units")))
    canvas_catalog.bind("<Leave>", lambda event: canvas_catalog.unbind_all("<MouseWheel>"))
    
    #===== Cria um Frame dentro do Canvas
    frame_internal = tk.Frame(canvas_catalog, bg = "white")

    #===== Adiciona o Frame Internal ao Canvas
    frame_id = canvas_catalog.create_window((0, 0), window=frame_internal, anchor="nw")
    #===== Quando o Frame for alterado executa a função frame configure
    frame_internal.bind("<Configure>", lambda event: on_frame_configure(canvas_catalog))
    #===== Quando o canvas for alterado executa a função resize_frame
    canvas_catalog.bind('<Configure>', lambda event: resize_frame(event, canvas_catalog, frame_internal,frame_id))

    catalog(frame_internal,imageHacktux, canvas_catalog,scroll_bar)

    # ===== Serve para que a janela quando o progrma é inciado ficar à frente e não atrás das outras janelas
    # ===== Quando se inciava o vrest isso acontecia
    root.lift()
    root.attributes('-topmost',1)
    root.attributes('-topmost',0)

    root.mainloop()

if __name__ == "__main__":
    main()

