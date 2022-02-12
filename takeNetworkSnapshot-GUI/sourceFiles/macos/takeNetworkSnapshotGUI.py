# Netmiko ile network otomasyonu
# by Rauf KARAKAŞ

import os.path
from datetime import datetime
from functools import partial
from threading import *
from tkinter import *
from tkinter import scrolledtext
from tkinter import ttk

from IPython.display import display, HTML
from netmiko import ConnectHandler
from netmiko.ssh_exception import AuthenticationException
from netmiko.ssh_exception import NetMikoTimeoutException
from paramiko.ssh_exception import SSHException
from pyvis import network as net


################ APP LOGIC ##############
# Fonksiyonlari tanimla
def getCdpItems(output):
    """CDP'de gorunen cihazları port:hostname şeklinde dictionary olarak return eder."""
    try:
        cdpDict = {}
        # CDP ciktisinda "Port ID\n" kelimesinin index'ini bulup, kalan string'i elde et
        cdpOutput = output[(output.find("Port ID\n") + 7):]

        # Gereksiz karakterleri sil, string'i listeye cevir
        while "  " in cdpOutput:
            cdpOutput = cdpOutput.replace("  ", " ")
        cdpOutput = cdpOutput.split(" ")

        # Liste uzerinde "\n" karakterini iceren ogeler ve sonraki 2 ogeyi dict'e ekle
        # Swname\n Eth 0/1
        for i in range(len(cdpOutput)):
            if "\n" in cdpOutput[i]:
                swName = cdpOutput[i].replace("\n", "")
                while "/" in swName:
                    swName = swName[(swName.find("/") + 1):]
                while swName[0].isdigit() or swName[0] == ".":
                    swName = swName[1:]
                if not swName.startswith("SEP"):  # IP telefonlari CDP tablosundan cikar
                    # Isımlendirilmemis AP'leri tum ismi ile al (MAC adresi)
                    # Switch domain name'i sil
                    if "." in swName and not swName.startswith("AP"):
                        swName = swName[:(swName.find("."))]
                    if i + 2 < len(cdpOutput):
                        portName = cdpOutput[i + 1] + " " + cdpOutput[i + 2]
                        cdpDict[portName] = swName
                        i = i + 2
        if "cdp entries" in cdpDict:
            cdpDict.pop("cdp entries")
        writeToLogfile("BILGI: CDP dictionary basariyla oluşturuldu.")
        return cdpDict
    except:
        writeToLogfile("HATA: CDP dictionary olusturulamadı.")
        return None


def getFullConfig(session):
    """Cihazda 'show run' ciktisini çalıştırıp, return eder."""
    try:
        deviceConfig = session.send_command("show running-config")
        writeToLogfile("BILGI: Cihaz konfigurasyonu SSH ile basariyla alindi.")
        return deviceConfig
    except:
        writeToLogfile("HATA: Cihaz konfigurasyonu SSH ile alinamadi.")
        return None


def createConfigBackupFile(configString, switch):
    """configBackups klasorune switch konfigurasyonunu kaydeder."""
    try:
        fileName = "configBackup_" + switch.replace(".", "_") + ".txt"
        path = "configBackups"
        configPath = os.path.join(path, fileName)
        with open(configPath, "w", encoding="utf-8") as configFile:
            configFile.write(configString)
        configFile.close()
    except:
        writeToLogfile("HATA: Switch konfigurasyon dosyasi olusturulamadi.")


def writeToLogfile(log):
    """Girilen log metnini txt dosyasina kaydeder ve konsola yazdirir."""
    log_data = "{}: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), log)
    with open("logs.txt", "a") as log_file:
        log_file.write(log_data)
    log_file.close()
    logBox.insert(END, log_data)
    logBox.see("end")


def takeNetworkSnapshot():
    # Butonu devre disi birak
    runButton.config(state="disabled")
    # Konfigurasyon icin ortami hazirla
    try:
        configBackupRequested = configBackupSelected.get()
        topologyRequested = createTopologySelected.get()
        # switchList.txt dosyasindan IP adreslerini oku ve listeye ekle
        switchList = []
        try:
            ipListBoxValue = ipListBox.get('1.0', 'end-1c').split("\n")
            for item in ipListBoxValue:
                if len(item) > 1:
                    switchList.append(item.strip())
            writeToLogfile("BILGI: Switch IP listesi olusturuldu. %d switch bulundu." % len(switchList))
        except:
            writeToLogfile("HATA: Switch IP bilgileri alinamadi. Iptal ediliyor...")
            os.abort()
        # Switch giris bilgilerini al
        user = username.get()
        password = passwordValue.get()
        if secretCheckboxSelected.get():
            enablePassword = password
        else:
            enablePassword = enablePasswordValue.get()
        if configBackupRequested:
            if not os.path.isdir("configBackups"):
                os.mkdir("configBackups")
    except:
        writeToLogfile("HATA: On bilgiler alinamadi. Iptal ediliyor...")
        os.abort()

    # Her switch icin CDP ciktisini al
    switchTreeDict = {}  # Switch altindaki switchlerin tutuldugu dict
    switchTreeDatailedDict = {}  # Switch altindaki switchlerin port numaralariyla birlikte tutuldugu dict
    switchIPDict = {}
    for switchIP in switchList:
        try:
            ciscoSwitch = {'device_type': 'cisco_ios', 'host': switchIP,
                           'username': user, 'password': password,
                           'secret': enablePassword, 'port': 22, }
            ssh = ConnectHandler(**ciscoSwitch)
            ssh.enable()
            writeToLogfile("BILGI: %s IP adresli switch'e baglanildi." % switchIP)
            swName = ssh.find_prompt()
            swName = swName[:-1]
            switchIPDict[swName] = switchIP
            writeToLogfile("BILGI: Switch hostname: %s " % swName)
            if configBackupRequested:  # Switch konfigurasyon yedegi al
                rawSwConfig = getFullConfig(ssh)
                createConfigBackupFile(rawSwConfig, switchIP)
                writeToLogfile("BILGI: Switch konfigurasyonu 'configBackups' klasorune kaydedildi.")
            if topologyRequested:
                cdpOutput = ssh.send_command("show cdp neighbors")
                cdpDict = getCdpItems(cdpOutput)
                switchTreeDict[swName] = list(cdpDict.values())
                switchTreeDatailedDict[swName] = cdpDict
            # SSH baglantisini sonlandir
            ssh.disconnect()
        except (NetMikoTimeoutException):
            writeToLogfile("HATA: %s IP adresli switch'e baglanilamadi. Timeout." % switchIP)
            continue
        except (AuthenticationException):
            writeToLogfile("HATA: %s IP adresli switch'e baglanilamadi. Parola hatali." % switchIP)
            continue
        except (SSHException):
            writeToLogfile("HATA: %s IP adresli switch'e SSH ile baglanilamadi. Telnet ile deneyin." % switchIP)
            continue
        except:
            writeToLogfile("HATA: %s IP adresli switch işlenirken hata oluştu." % switchIP)
            continue

    # Topolojiyi ciz
    if topologyRequested:
        try:
            graphOptions = {
                "edges": {
                    "color": {
                        "inherit": True
                    },
                    "smooth": False
                },
                "manipulation": {
                    "enabled": True
                },
                "interaction": {
                    "hover": True
                },
                "physics": {
                    "barnesHut": {
                        "damping": 0.6,
                        "avoidOverlap": 0.01,
                        "springLength": 115
                    },
                    "minVelocity": 0.75
                }
            }

            # CDP verisi alinan switchlerin hostname'lerini nodeList'e ekle
            nodeList = list(switchTreeDict.keys())
            # CDP verisi alinan switchlere bagli alt switchleri edgeList'e ekle
            edgeList = list(switchTreeDict.values())
            # Grafik ortamini olustur
            networkGraph = net.Network(height='100%', width='100%', heading='')
            # Node ve edge listesi icindeki tum benzersiz switchleri nodesToAdd listesine ekle
            nodesToAdd = []
            for node in nodeList:
                if node not in nodesToAdd:
                    nodesToAdd.append(node)
            for subList in edgeList:
                for edge in subList:
                    if edge not in nodesToAdd:
                        nodesToAdd.append(edge)
            # Benzersiz switch'leri ve AP'leri node olarak ekle
            for node in nodesToAdd:
                if node in nodeList:
                    if node in switchIPDict:
                        nodeDetail = "IP: %s %s" % (str(switchIPDict[node]), str(switchTreeDatailedDict[node]))
                    else:
                        nodeDetail = str(switchTreeDatailedDict[node])
                if "sw" in node.lower():  # Node switch ise varsayılan gorunumu kullan
                    networkGraph.add_node(node, title=nodeDetail)
                elif "ap" in node.lower():  # Node AP ise yesile boya
                    networkGraph.add_node(node, title=nodeDetail, color="lightgreen")
                else:  # Diger node'lari griye boya
                    networkGraph.add_node(node, title=nodeDetail, color="lightgray")
            # nodeList ve edgeList listeleri ile grafigi olustur
            for i in range(len(nodeList)):
                node = nodeList[i]
                for edge in edgeList[i]:
                    if node != edge:
                        networkGraph.add_edge(node, edge, color="black")
            networkGraph.toggle_physics(True)
            # networkGraph.show_buttons() # Tum ayar menusunu goster
            networkGraph.options = graphOptions
            networkGraph.show("networkTopology.html")
            display(HTML("networkTopology.html"))
            writeToLogfile("Bilgi: Topolojiye 'networkTopology.html' dosyasindan ulasilabilir.")
        except:
            writeToLogfile("HATA: Topoloji olusturulurken hata olustu.")
    writeToLogfile("BILGI: Islem tamamlandi.")
    runButton.config(state="normal")


def appThreading():
    """Uygulamayi ayri bir thread olarak calistir"""
    workThread = Thread(target=takeNetworkSnapshot)
    workThread.start()


# Arayuz fonksiyonlari
# Enable parolasi kutusunu checkbox durumuna gore aktif veya deaktif et
def secretCheckboxChanged():
    if not secretCheckboxSelected.get():
        enablePasswordEntry.config(state="normal")
    else:
        enablePasswordEntry.config(state="disabled")


# Config ya da topology secimlerine gore butonu aktif veya deaktif et
def activateRunButton():
    if configBackupSelected.get() or createTopologySelected.get():
        runButton.config(state="normal")
    else:
        runButton.config(state="disabled")


# Uygulama ekrani temel parametreler
appWindow = Tk()
appWindow.title("Network Snapshot Taker for Cisco IOS")
appWindow.geometry("700x600")
appWindow.resizable(False, False)

# Kullanici adi, parola ve secenek secim menuleri
# Kullanici adi
usernameLabel = Label(appWindow, text="Username:")
usernameLabel.grid(row=0, column=0, sticky="w", padx=10)
username = StringVar()
usernameEntry = Entry(appWindow, textvariable=username)
usernameEntry.grid(row=0, column=1)
# Parola
passwordLabel = Label(appWindow, text="Password:")
passwordLabel.grid(row=1, column=0, sticky="w", padx=10)
passwordValue = StringVar()
passwordEntry = Entry(appWindow, textvariable=passwordValue, show='*')
passwordEntry.grid(row=1, column=1)
# Enable parolasi
enablePasswordLabel = Label(appWindow, text="Enable Password:")
enablePasswordLabel.grid(row=2, column=0, sticky="w", padx=10)
enablePasswordValue = StringVar()
enablePasswordEntryState = "disabled"
enablePasswordEntry = Entry(appWindow, textvariable=enablePasswordValue, show='*', state=enablePasswordEntryState)
enablePasswordEntry.grid(row=2, column=1)

################# Ayrac #################
valueSeparator = ttk.Separator(appWindow, orient="vertical")
valueSeparator.grid(row=0, column=3, rowspan=3, sticky='ns', padx=15)

# Konfigurasyon ve topology buton aktiflik kontrolu
backupTopologyCommand = partial(activateRunButton)
# Konfigurasyon yedeklemesi
configBackupSelected = BooleanVar(value=True)
configBackupCheckbox = Checkbutton(appWindow, text="Take configuration backups", variable=configBackupSelected,
                                   onvalue=True, offvalue=False, command=backupTopologyCommand)
configBackupCheckbox.grid(row=0, column=4, columnspan=2, sticky="w")
# Topoloji olustur
createTopologySelected = BooleanVar(value=True)
createTopologyCheckbox = Checkbutton(appWindow, text="Create network topology", variable=createTopologySelected,
                                     onvalue=True, offvalue=False, command=backupTopologyCommand)
createTopologyCheckbox.grid(row=1, column=4, columnspan=2, sticky="w")
# Enable parolasi (secret) checkbox
secretCheckboxSelected = BooleanVar(value=True)
secretCheckboxCommand = partial(secretCheckboxChanged)
secretCheckbox = Checkbutton(appWindow, text="Secret is not required or same with password.",
                             variable=secretCheckboxSelected,
                             onvalue=True, offvalue=False, command=secretCheckboxCommand)
secretCheckbox.grid(row=2, column=4, columnspan=2, sticky="w")

################# Ayrac #################
inputSeparator = ttk.Separator(appWindow, orient="horizontal")
inputSeparator.grid(row=3, column=0, columnspan=6, sticky='we', pady=10)

# IP listesi girdi kutusu
ipListLabel = Label(appWindow, text="Switch IP List")
ipListLabel.grid(row=4, column=0)
# ipList = StringVar()
ipListBox = scrolledtext.ScrolledText(appWindow, wrap=WORD, width=16, height=25,
                                      highlightthickness=2, highlightbackground="gray")
ipListBox.grid(row=5, column=0, rowspan=2, sticky="w", padx=10)
ipListBox.focus()

# Log bilgi kutusu
logBoxLabel = Label(appWindow, text="Logs")
logBoxLabel.grid(row=4, column=1, columnspan=5)
logBox = scrolledtext.ScrolledText(appWindow, wrap=WORD, width=75, height=25,
                                   highlightthickness=2, highlightbackground="gray")
logBox.grid(row=5, column=1, rowspan=2, columnspan=5, sticky="w")

################# Ayrac #################
inputSeparator = ttk.Separator(appWindow, orient="horizontal")
inputSeparator.grid(row=7, column=0, columnspan=6, sticky='we', pady=15)

# Calistir butonu
runButtonCommand = partial(takeNetworkSnapshot)
runButton = Button(appWindow, text="Take Network Snapshot",
                   font=("Calibri", 14, "bold"), command=appThreading)
runButton.grid(row=8, column=0, columnspan=6, sticky='we', padx=10)

################# Ayrac #################
inputSeparator = ttk.Separator(appWindow, orient="horizontal")
inputSeparator.grid(row=9, column=0, columnspan=6, sticky='we', pady=10)

# Imza
signatureLabel = Label(appWindow, text="Developed on Feb 2022 by Rauf KARAKAS", font=("Calibri", 8))
signatureLabel.grid(row=9, column=0, columnspan=6, sticky='e', padx=10, pady=10)

versionLabel = Label(appWindow, text="Version 1.0", font=("Calibri", 8))
versionLabel.grid(row=9, column=0, columnspan=6, sticky='w', padx=10, pady=10)

# GUI'yi goster
appWindow.mainloop()
