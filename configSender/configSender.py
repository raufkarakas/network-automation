# Netmiko ile network otomasyonu
# by Rauf KARAKAŞ

from netmiko import ConnectHandler
from datetime import datetime
from getpass import getpass
import os.path


# Kullanılacak fonksiyonlari tanimla

def writeToLogfile(log):
    """Girilen log metnini txt dosyasina kaydeder ve konsola yazdirir."""
    log_data = "{}: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), log)
    with open("logs.txt", "a") as log_file:
        log_file.write(log_data)
    log_file.close()
    print(log_data)


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


def getUserAnswer(question):
    """Kullaniciya sorulan e/h sorusunun cevabini return eder."""
    answer = ""
    errorActive = False
    while answer not in ["e", "h"]:
        if errorActive:
            print("Hatali girdi. Tekrar deneyin.")
        answer = input(question + " (e/h): ")
        answer = answer.strip().lower()
        errorActive = True
    if answer == "e":
        return True
    return False


# Konfigurasyon icin ortami hazirla
try:
    # switchList.txt dosyasindan IP adreslerini oku ve listeye ekle
    switchList = []
    try:
        with open("switchList.txt") as file:
            for line in file:
                if len(line) > 1:
                    switchList.append(line.strip())
        writeToLogfile("BILGI: Switch IP listesi olusturuldu. %d switch bulundu." % len(switchList))
    except:
        writeToLogfile("HATA: Switch IP bilgileri alinamadi. Iptal ediliyor...")
        os.abort()
    # configFile.txt dosyasindan uygulanacak konfigurasyonlari oku ve listeye ekle
    configList = []
    try:
        with open("configFile.txt") as file:
            for line in file:
                if len(line) > 1:
                    configList.append(line.strip())
        writeToLogfile("BILGI: Konfigurasyon listesi olusturuldu.")
    except:
        writeToLogfile("HATA: Konfigurasyon bilgileri alinamadi. Iptal ediliyor...")
        os.abort()
    # Listelerin bos olmadigina emin ol
    if len(switchList) == 0 or len(configList) == 0:
        writeToLogfile("HATA: IP ya da konfigurasyon dosyalarinda eksik bilgi. Iptal ediliyor...")
        os.abort()
    # Konfigurasyonun kaydedilmesi isteniyor mu, bilgi al
    wantToSaveConfig = getUserAnswer("Islem sonunda konfigurasyon kaydedilsin mi?")
    # Switch giris bilgilerini al
    user = input("Username: ")
    password = getpass(prompt="Password: ")
    enablePassword = password
    # Komut ciktilarinin saklanacagi klasoru olustur
    if not os.path.isdir("commandOutputs"):
        os.mkdir("commandOutputs")
except:
    writeToLogfile("HATA: On bilgiler alinamadi. Iptal ediliyor...")
    os.abort()

# Switchleri konfigure et
for switchIP in switchList:
    try:
        ciscoSwitch = {'device_type': 'cisco_ios', 'host': switchIP,
                       'username': user, 'password': password,
                       'secret': enablePassword, 'port': 22, }
        ssh = ConnectHandler(**ciscoSwitch)
        ssh.enable()
        writeToLogfile("BILGI: %s IP adresli switch'e baglanildi." % switchIP)
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
