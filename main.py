from network import WLAN
wlan = WLAN()

wlan.init(mode=WLAN.AP, ssid='hello world')
#use the line below to apply a password
#wlan.init(ssid="hi", auth=(WLAN.WPA2, "eightletters"))
print(wlan.ifconfig(id=1)) #id =1 signifies the AP interface
