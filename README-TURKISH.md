## configSender

configFile.txt dosyasında belirtilen konfigürasyonu switchList.txt dosyasında IP adresleri yazılı switchlere bağlanarak uygular. 

## multiConfigSender

multiConfigFile.txt dosyasını girdi olarak alır. Dosyada switch IP adresi başına # karakteri eklenerek yazılır. Altına ilgili IP adresli switch'e uygulanacak konfigürasyon eklenir. Bu sayede farklı switchlere farklı konfigürasyon uygulanabilmiş olur.

## takeNetworkSnapshot

switchList.txt dosyasında IP adresleri belirtilen switchlere bağlanarak konfigürasyon yedeklerini alır. Switchlere bağlı, CDP'de görünen diğer cihazların listesini tutar ve bağlantıların topolojisini çıkarır. Yedek alınması ve topoloji çıkarılması tek başına da uygulanabilir.