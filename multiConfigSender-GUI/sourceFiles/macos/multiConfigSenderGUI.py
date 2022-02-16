# Netmiko ile network otomasyonu
# by Rauf KARAKAŞ

import os.path
from datetime import datetime
from functools import partial
from threading import *
from tkinter import *
from tkinter import scrolledtext
from tkinter import ttk
from netmiko import ConnectHandler


################ APP LOGIC ##############
# Fonksiyonlari tanimla
def writeToLogfile(log):
    """Girilen log metnini txt dosyasina kaydeder ve konsola yazdirir."""
    log_data = "{}: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), log)
    with open("logs.txt", "a") as log_file:
        log_file.write(log_data)
    log_file.close()
    logBox.insert(END, log_data)
    logBox.see("end")


def logCommandOutputs(log, switch):
    """configBackups klasorune switch konfigurasyonunu kaydeder."""
    try:
        fileName = "commandOutputs_" + switch.replace(".", "_") + ".txt"
        path = "commandOutputs"
        configPath = os.path.join(path, fileName)
        with open(configPath, "a", encoding="utf-8") as configFile:
            configFile.write(log)
        configFile.close()
        return log
    except:
        writeToLogfile("HATA: Switch konfigurasyon dosyasi olusturulamadi.")


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


def multiConfigSender():
    try:
        # Butonu devre disi birak
        runButton.config(state="disabled")
        # Konfigurasyon icin ortami hazirla
        try:
            configDict = {}
            configInputList = configListBox.get('1.0', 'end-1c').split("\n")
            print(configInputList)
            for item in configInputList:
                if len(item) > 1:
                    # Satir basindaki ve sonundaki bosluklari sil
                    line = item.strip()
                    print(line)
                    # IP belirteci (#) olan satiri dict'e key olarak ekle ve karsiligina bos liste ata
                    # Dict yapisi IP-adresi : [config] seklinde olacak
                    if line.startswith("#"):
                        currentKey = line.replace("#", "").strip()
                        configDict[currentKey] = []
                    else:  # Dict value'a konfigurasyonlari ekle
                        configDict[currentKey].append(line)
            writeToLogfile("BILGI: Konfigurasyon veritabani olusturuldu. %d switch bulundu." % len(configDict))
        except:
            writeToLogfile("HATA: Konfigurasyon bilgileri alinamadi. Iptal ediliyor...")
            os.abort()
        # Listelerin bos olmadigina emin ol
        if len(configDict) == 0:
            writeToLogfile("HATA: Switch IP adresi bulunamadi. Iptal ediliyor...")
            os.abort()
        # Konfigurasyonun kaydedilmesi isteniyor mu, bilgi al
        wantToSaveConfig = saveConfigSelected.get()
        # Switch giris bilgilerini al
        user = usernameValue.get()
        password = passwordValue.get()
        if secretCheckboxSelected.get():
            enablePassword = password
        else:
            enablePassword = enablePasswordValue.get()
        if not os.path.isdir("commandOutputs"):
            os.mkdir("commandOutputs")
    except:
        writeToLogfile("HATA: On bilgiler alinamadi. Iptal ediliyor...")
        os.abort()
    # Switchleri konfigure et
    switchList = list(configDict.keys())
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
            writeToLogfile("BILGI: Switch hostname: %s " % swName)
            # CDP ciktisina göre interface description'i gir
            if cdpDescriptionRequested:
                cdpOutput = ssh.send_command("show cdp neighbors")
                cdpDict = getCdpItems(cdpOutput)
                for port in cdpDict:
                    descriptionConfigList = []
                    descriptionConfigList.append("interface %s" % port)
                    descriptionConfigList.append("description %s" % cdpDict[port])
                    logCommandOutputs(ssh.send_config_set(descriptionConfigList), switchIP)
                writeToLogfile("BILGI: CDP ciktilarina gore ilgili interface decription'lari guncellendi.")
            # Kullanici tarafindan girilen konfigurasyonu uygula
            configList = configDict[switchIP]
            logCommandOutputs(ssh.send_config_set(configList), switchIP)
            writeToLogfile("BILGI: Konfigurasyon listesi uygulandi.")
            if wantToSaveConfig:
                logCommandOutputs(ssh.send_command("write"), switchIP)
                writeToLogfile("BILGI: Switch (%s) konfigurasyonu kaydedildi." % switchIP)
            ssh.disconnect()
            writeToLogfile("BILGI: Switch (%s) baglantisi kapatildi." % switchIP)
        except:
            writeToLogfile("HATA: Switch (%s) konfigure edilirken hata olustu." % switchIP)
    writeToLogfile("BILGI: Islem tamamlandi.")
    runButton.config(state="normal")


def appThreading():
    """Uygulamayi ayri bir thread olarak calistir"""
    workThread = Thread(target=multiConfigSender)
    workThread.start()


# Arayuz fonksiyonlari
# Enable parolasi kutusunu checkbox durumuna gore aktif veya deaktif et
def secretCheckboxChanged():
    if not secretCheckboxSelected.get():
        enablePasswordEntry.config(state="normal")
    else:
        enablePasswordEntry.config(state="disabled")


# Uygulama ekrani temel parametreler
appWindow = Tk()
appWindow.title("Multiple Configurator for Cisco IOS")
appWindow.geometry("700x655")
appWindow.resizable(False, False)

# Kullanici adi, parola ve secenek secim menuleri
# Kullanici adi
usernameLabel = Label(appWindow, text="Username:")
usernameLabel.grid(row=0, column=0, sticky="w", padx=10)
usernameValue = StringVar()
usernameEntry = Entry(appWindow, textvariable=usernameValue)
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
################# Ayrac #################

# Konfigurasyon kaydetme tercihi
saveConfigSelected = BooleanVar(value=True)
saveConfigCheckbox = Checkbutton(appWindow, text="Save configuration after changes.",
                                 variable=saveConfigSelected, onvalue=True, offvalue=False)
saveConfigCheckbox.grid(row=0, column=4, columnspan=2, sticky="w")

# CDP description tercihi
cdpDescriptionRequested = BooleanVar(value=True)
cdpDescriptionCheckbox = Checkbutton(appWindow, text="Add interface descriptions based on CDP table.",
                                     variable=cdpDescriptionRequested, onvalue=True, offvalue=False)
cdpDescriptionCheckbox.grid(row=1, column=4, columnspan=2, sticky="w")

# Enable parolasi (secret) checkbox
secretCheckboxSelected = BooleanVar(value=True)
secretCheckboxCommand = partial(secretCheckboxChanged)
secretCheckbox = Checkbutton(appWindow, text="Secret is not required or same with password.",
                             variable=secretCheckboxSelected, onvalue=True,
                             offvalue=False, command=secretCheckboxCommand)
secretCheckbox.grid(row=2, column=4, columnspan=2, sticky="w")

################# Ayrac #################
inputSeparator = ttk.Separator(appWindow, orient="horizontal")
inputSeparator.grid(row=3, column=0, columnspan=6, sticky='we', pady=10)
################# Ayrac #################

# Switch ve konfig detaylarini iceren label ve kutu
configListLabel = Label(appWindow,
                        text="Configuration box (Place # before the IP, and add the configuration below it.)")
configListLabel.grid(row=4, column=0, columnspan=6)
# Kutucuk
configListBox = scrolledtext.ScrolledText(appWindow, wrap=WORD, width=90, height=20,
                                          highlightthickness=2, highlightbackground="gray")
configListBox.grid(row=5, column=0, columnspan=6, rowspan=2, sticky="we", padx=10)
configListBox.focus()

# Log bilgi kutusu
logBoxLabel = Label(appWindow, text="Logs")
logBoxLabel.grid(row=7, column=0, columnspan=6)
logBox = scrolledtext.ScrolledText(appWindow, wrap=WORD, width=90, height=7,
                                   highlightthickness=2, highlightbackground="gray")
logBox.grid(row=8, column=0, columnspan=6, rowspan=2, sticky="we", padx=10)

################# Ayrac #################
inputSeparator = ttk.Separator(appWindow, orient="horizontal")
inputSeparator.grid(row=10, column=0, columnspan=6, sticky='we', pady=15)
################# Ayrac #################

# Calistir butonu
runButtonCommand = partial(multiConfigSender)
runButton = Button(appWindow, text="Configure Multiple Switches",
                   font=("Calibri", 14, "bold"), command=appThreading)
runButton.grid(row=11, column=0, columnspan=6, sticky='we', padx=10)

################# Ayrac #################
inputSeparator = ttk.Separator(appWindow, orient="horizontal")
inputSeparator.grid(row=12, column=0, columnspan=6, sticky='we', pady=10)
################# Ayrac #################

# Imza
signatureLabel = Label(appWindow, text="Developed on Feb 2022 by Rauf KARAKAS", font=("Calibri", 8))
signatureLabel.grid(row=12, column=0, columnspan=6, sticky='e', padx=10, pady=10)

versionLabel = Label(appWindow, text="Version 1.0", font=("Calibri", 8))
versionLabel.grid(row=12, column=0, columnspan=6, sticky='w', padx=10, pady=10)

# GUI'yi goster
appWindow.mainloop()
