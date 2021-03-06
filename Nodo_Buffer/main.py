import os
import socket
import time
import struct
import pycom
import ubinascii, network
from network import LoRa
import machine

from LoraPack import *
from env_recv import *
import _thread

#lock = _thread.allocate_lock()

# A basic package header, B: 1 byte for the deviceId, B: 1 byte for the pkg size, %ds: Formatted string for string
_LORA_PKG_FORMAT = "!BBIBB"


# A basic ack package, B: 1 byte for the deviceId, B: 1 byte for the pkg size, B: 1 byte for the Ok (200) or error messages
_LORA_PKG_ACK_FORMAT = "!BBIB"

MAX_RECV = 1
MAX_BUFFER = 4

#Activador de comprobacion de mensaje
ACK_ACTV = 0

#Activador de modo Test
modeTEST = 1

#Activador de suspesion del sistema
ModeSleep = 0

# Open a LoRa Socket, use rx_iq to avoid listening to our own messages
# Please pick the region that matches where you are using the device:
# Asia = LoRa.AS923
# Australia = LoRa.AU915
# Europe = LoRa.EU868
# United States = LoRa.US915

lora = LoRa(mode=LoRa.LORA, region=LoRa.US915)
lora_sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
lora_sock.setblocking(False)
location = 0x01
id_device = Def_ID(lora)
count = 100
send_OK = 0
cuenta_recibo = 0
list_recv = []          # LISTA DE LOS ID DE LOS MENSAJES RECIBIDOS


active_sleep = 0

buffer = []            # LISTA DE LOS MENSAJES EN BUFFER A ENVIAR

List_send = ID_recv()    #LISTA DE CONTEO PARA ACK

if ACK_ACTV:

    pycom.heartbeat(False)


#lista ID para enviar y bloquear
if(modeTEST):
    namefile = "ID" + str(id_device)
    ID_block = Open_Test(namefile)


def Send_buffer():
    global lora, lora_sock, location, id_device, list_recv, active_sleep

    while(True):
        if len(buffer)>0:
            #if id_send not in list:
        #ENVIO
            send_pck = buffer.pop(0)
            id_to_send, id_end, UID_msg = get_IDdest(send_pck)
            if(id_to_send == id_device):
                lora_sock.send(send_pck)
            else:
                print("Reenvio de: %d" % id_to_send)
                pck_reenvio = set_IDorigen(send_pck, id_device)
                lora_sock.send(pck_reenvio)
        elif active_sleep and ModeSleep:
            print("Sleep")
            machine.sleep(1000*20,False)
            lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)
            print("Wake up")
            active_sleep = 0
        if ModeSleep:
            time.sleep(2)


def Packet_buffer(ID_send):
    global location, id_device, list_recv, buffer, active_sleep
    cuenta_envio = 0
    while(True):
        if(ID_send):
        #ENVIO AL BUFFER
            if ModeSleep:
                if not active_sleep:
                    time.sleep(4)
                    UID = UID_message(id_device)
                    list_recv.append(UID)
                    pck = pack_Lora(id_device, ID_send, UID, 0, location)
                    if(len(buffer) < MAX_BUFFER):
                        cuenta_envio = cuenta_envio + 1
                        print("Numero de paquetes enviados: %d" % cuenta_envio)
                        buffer.append(pck)
                    active_sleep = 1
            else:
                UID = UID_message(id_device)
                list_recv.append(UID)
                pck = pack_Lora(id_device, ID_send, UID, location, 0)
                if(len(buffer) < MAX_BUFFER):
                    cuenta_envio = cuenta_envio + 1
                    print("Numero de paquetes enviados: %d" % cuenta_envio)
                    buffer.append(pck)
                time.sleep(15)


def Recv():
    global lora, lora_sock, location, id_device, list_recv, modeTEST, buffer, count, active_sleep, cuenta_recibo

    #Recibo
    recv_pkg = lora_sock.recv(256)
    recv_pkg_len = recv_pkg[1]
    id_to_send, id_end, UID_msg = get_IDdest(recv_pkg)

    if(modeTEST):
        if id_to_send in ID_block:
            return
    if UID_msg in list_recv:
        return
    else:
        list_recv.append(UID_msg)

    if (len(recv_pkg) > 7):
        if(id_end == id_device):
            id_to_send, id_end, UID_msg, TTL, location = unpack_Lora(recv_pkg,  recv_pkg_len)
            cuenta_recibo = cuenta_recibo + 1
            print("Mensaje para mi de %d. Saltos:%d" % (get_SendID(UID_msg), TTL))
            TTL = TTL + 1
            print("Cuenta recibida de paquetes %d" % cuenta_recibo)
            if List_ack(get_SendID(UID_msg), List_send) and ACK_ACTV:
                send_ack(get_SendID(UID_msg))
            if ModeSleep:
                time.sleep(5)
                if not len(buffer):
                    active_sleep = 1
        else:
            if(len(buffer) < MAX_BUFFER):
                buffer.append(recv_pkg)
                if ModeSleep:
                    time.sleep(5)
                    active_sleep = 1

    elif (len(recv_pkg) > 2 and len(recv_pkg) < 8 and ACK_ACTV):
        if(id_end == id_device):
            id_to_send, id_end, UID_msg, TTL = unpack_AckLora(recv_pkg,  recv_pkg_len)
            TTL = TTL + 1
            print("Recibo un ACK. Saltos %d" % TTL)
            send_OK = 1
            pycom.rgbled(0x007f00)
            count = 100
        else:
            if(len(buffer) < MAX_BUFFER):
                buffer.append(recv_pkg)


def send_ack(id_respond):
    global lora, lora_sock, list_recv, buffer
    UID = UID_message(id_device)
    list_recv.append(UID)
    pkg_ack = pack_AckLora( id_device, id_respond, UID, 0)
    buffer.append(pkg_ack)


def clear():
    global list_recv
    time.sleep(200)
    list_recv = []


def ack_off():
    global  count , send_OK
    while(ACK_ACTV):
        time.sleep(1)
        count = count - 1
        if not count:
            pycom.rgbled(0x7f0000)
            send_OK = 0


def lora_cb(lora):
    events = lora.events()
    if events & LoRa.RX_PACKET_EVENT:
        Recv()

lora.callback(trigger=(LoRa.RX_PACKET_EVENT | LoRa.TX_PACKET_EVENT), handler=lora_cb)

def Send(ID_send):
    _thread.start_new_thread(Packet_buffer, (ID_send, ))



time.sleep(10)

_thread.start_new_thread(Send_buffer, ())

_thread.start_new_thread(ack_off, ())

_thread.start_new_thread(clear,())
