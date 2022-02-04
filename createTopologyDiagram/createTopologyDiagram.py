# Netmiko ile network otomasyonu
# by Rauf KARAKAŞ

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException
from netmiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import SSHException
from datetime import datetime
from getpass import getpass
import os.path
from pyvis import network as net
from IPython.display import display, HTML

switchList = ["172.16.2.253",
              "172.16.2.11",
              "172.16.2.22",
              "172.16.2.33",
              "172.16.2.44",
              "172.16.2.55"]


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
except:
    writeToLogfile("HATA: On bilgiler alinamadi. Iptal ediliyor...")
    os.abort()

# Her switch icin CDP ciktisini al
switchTreeDict = {}  # Switch altindaki switchlerin tutuldugu dict
switchTreeDatailedDict = {}  # Switch altindaki switchlerin port numaralariyla birlikte tutuldugu dict
for switchIP in switchList:
    try:
        ciscoSwitch = {'device_type': 'cisco_ios', 'host': switchIP,
                       'username': user, 'password': password,
                       'secret': enablePassword, 'port': 22, }
        ssh = ConnectHandler(**ciscoSwitch)
        writeToLogfile("BILGI: %s IP adresli switch'e baglanildi." % switchIP)
        ssh.enable()
        swName = ssh.find_prompt()
        swName = swName[:-1]
        writeToLogfile("BILGI: Switch hostname: %s " % swName)
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
                "damping": 0.6
            },
            "minVelocity": 0.75
        }
    }

    # CDP verisi alinan switchlerin hostname'lerini nodeList'e ekle
    nodeList = list(switchTreeDict.keys())
    # CDP verisi alinan switchlere bagli alt switchleri edgeList'e ekle
    edgeList = list(switchTreeDict.values())
    # Grafik ortamini olustur
    networkGraph = net.Network(height='600px', width='100%', heading='')
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
        nodeDetail = node
        if node in nodeList:
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
