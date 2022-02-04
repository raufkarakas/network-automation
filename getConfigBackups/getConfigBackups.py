# Netmiko ile network otomasyonu
# by Rauf KARAKAŞ

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException
from netmiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import SSHException
from datetime import datetime
from getpass import getpass
import os.path

switchList = ["172.16.2.44",
              "172.16.2.55"]


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
    with open("configuration_log.txt", "a") as log_file:
        log_file.write(log_data)
    log_file.close()
    print(log_data)


# Konfigurasyon icin ortami hazirla
try:
    user = input("Username: ")
    password = getpass(prompt="Password: ")
    enablePassword = password
    if not os.path.isdir("configBackups"):
        os.mkdir("configBackups")
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
        writeToLogfile("BILGI: %s IP adresli switch'e baglanildi." % switchIP)
        ssh.enable()
        writeToLogfile("BILGI: Switch konfigurasyonu aliniyor.")
        rawSwConfig = getFullConfig(ssh)
        writeToLogfile("BILGI: Switch konfigurasyonu 'configBackups' klasorune kaydediliyor.")
        createConfigBackupFile(rawSwConfig, switchIP)
        ssh.disconnect()
        writeToLogfile("BILGI: SSH baglantisi sonlandirildi.")
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
