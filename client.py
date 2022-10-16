import socket
import json
from datetime import datetime
import random
import time
from _thread import *


# Local Machine
serverIP = '192.168.15.124'

# Local Server (LAN)
# serverIP = '192.168.1.30'

# Local Server (WAN)
# serverIP = '100.64.113.95'

# Google Cloud Server 2
# serverIP = '35.199.96.140'

# Amazon Cloud Server
# serverIP = '18.229.124.42'


class Client:
    def __init__(self):
        self.ClientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ClientSocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.host = serverIP

        self.port = 5555
        self.bufferSize = 4096
        self.commandQueue = []

        # Lock for TCP requisitions
        self.tcpLock = TCPLock()

        # Commands coming from server
        self.queue = Queue()

        # Client UDP Server
        self.UdpServer = UdpServer()


        print('Waiting for connection')
        try:
            self.ClientSocket.connect((self.host, self.port))
        except socket.error as e:
            print(str(e))

    def runConnection(self):
        while True:
            command = self.ClientSocket.recv(self.bufferSize)
            if command:
                while self.queue.lock:
                    pass
                self.queue.lock = True
                self.queue.insert(QueueElement(command))
                self.queue.lock = False
                print(self.queue.queue)

    def process_data(self):
        while True:
            t0 = datetime.now().microsecond
            if not self.queue.is_empty() and not self.queue.lock:
                self.queue.lock = True
                firstElement = self.queue.pop()
                self.queue.lock = False
                self.analyzeData(firstElement.connection, firstElement.address, firstElement.command.decode())
            print("ProcessData: " + str((datetime.now().microsecond - t0) / 1000))  # ms

    def getPlayerID(self):
        command = "GET"
        what = "PLAYER_ID"
        data = [command, what]
        jsonparam = json.dumps(data)
        self.tcpLock.acquire()
        self.ClientSocket.sendall(jsonparam.encode())
        ret = int(self.ClientSocket.recv(self.bufferSize).decode())
        self.tcpLock.release()
        return ret

    def getBombID(self):
        command = "GET"
        what = "BOMB_ID"
        data = [command, what]
        jsonparam = json.dumps(data)
        self.tcpLock.acquire()
        self.ClientSocket.sendall(jsonparam.encode())
        ret = int(self.ClientSocket.recv(self.bufferSize).decode())
        self.tcpLock.release()
        return ret

    def getServerParameters(self, selfPlayerID, roomID):
        command = "GET"
        what = "PLAYERS"
        data = [command, what, selfPlayerID, roomID]
        jsonparam = json.dumps(data)
        self.tcpLock.acquire()
        self.ClientSocket.sendall(jsonparam.encode())
        ret = self.ClientSocket.recv(self.bufferSize).decode()
        self.tcpLock.release()
        return ret

    def createPLayer(self, x, y, character, playerGUID):
        command = "CREATE"
        what = "PLAYER"
        data = [command, what, x, y, character, playerGUID]
        self.ClientSocket.send(json.dumps(data).encode())

    def createBomb(self, x, y, playerID, roomID):
        command = "CREATE"
        what = "BOMB"
        data = [command, what, x, y, playerID, roomID]
        self.tcpLock.acquire()
        self.ClientSocket.send(json.dumps(data).encode())
        bombID = self.ClientSocket.recv(self.bufferSize).decode()
        self.tcpLock.release()
        return int(bombID)

    def deletePlayer(self, playerID):
        command = "DELETE"
        what = "PLAYER"
        data = [command, what, playerID]
        print(str(datetime.now())+" DELETE PLAYER REQUESTED")
        self.ClientSocket.send(json.dumps(data).encode())

    def setPlayerPosition(self, pid, x, y, direction, roomID):
        command = "SET"
        what = "PLAYER_POSITION"
        data = [command, what, pid, x, y, direction, roomID]
        # self.UdpServer.sendMessage(json.dumps(data).encode())
        self.ClientSocket.send(json.dumps(data).encode())

    def getServerCommands(self, playerID, roomID):
        command = "GET"
        what = "COMMANDS"
        data = [command, what, playerID, roomID]
        self.tcpLock.acquire()
        self.ClientSocket.sendall(json.dumps(data).encode())
        recv = self.ClientSocket.recv(self.bufferSize).decode()
        self.tcpLock.release()
        ret = json.loads(recv)
        return ret

    def requestAutoJoin(self, playerGUID):
        command = "GET"
        what = "AUTOJOIN"
        data = [command, what, playerGUID]
        self.tcpLock.acquire()
        self.ClientSocket.sendall(json.dumps(data).encode())
        recv = self.ClientSocket.recv(self.bufferSize).decode()
        self.tcpLock.release()
        ret = json.loads(recv)
        return ret

    def createServerRoom(self, roomName, password, capacity):
        command = "CREATE"
        what = "ROOM"
        data = [command, what, roomName, password, capacity]
        jsonparam = json.dumps(data)
        self.tcpLock.acquire()
        self.ClientSocket.sendall(jsonparam.encode())
        ret = self.ClientSocket.recv(self.bufferSize).decode()
        ret = json.loads(ret)
        self.tcpLock.release()
        return ret

    def joinSpecificRoom(self, name, password, playerGUID):
        command = "GET"
        what = "JOIN_SPECIFIC"
        data = [command, what, name, password, playerGUID]
        self.tcpLock.acquire()
        self.ClientSocket.sendall(json.dumps(data).encode())
        recv = self.ClientSocket.recv(self.bufferSize).decode()
        self.tcpLock.release()
        ret = json.loads(recv)
        return ret

    def requestAllRooms(self):
        command = "GET"
        what = "ALL_ROOMS"
        data = [command, what]
        self.tcpLock.acquire()
        self.ClientSocket.sendall(json.dumps(data).encode())
        recv = self.ClientSocket.recv(self.bufferSize).decode()
        self.tcpLock.release()
        ret = json.loads(recv)
        return ret

    def requestLogin(self, username, password):
        command = "DB"
        what = "LOGIN"
        data = [command, what, username, password]
        self.tcpLock.acquire()
        self.ClientSocket.sendall(json.dumps(data).encode())
        recv = int(self.ClientSocket.recv(self.bufferSize).decode())
        print("recv:",recv)
        self.tcpLock.release()
        ret = recv
        print("type:",type(ret))
        print("ret:",ret)
        return ret

    def requestRegisterAccount(self, username, email, password):
        command = "DB"
        what = "REGISTER"
        data = [command, what, username, email, password]
        self.tcpLock.acquire()
        self.ClientSocket.sendall(json.dumps(data).encode())
        recv = self.ClientSocket.recv(self.bufferSize)
        print("received:",recv)
        recv = int(recv.decode())
        self.tcpLock.release()
        ret = recv
        print("type:",type(ret))
        print("ret:",ret)
        return ret


class TCPLock:
    def __init__(self):
        self.lock = False

    def acquire(self):
        while self.lock:
            pass
        self.lock = True

    def release(self):
        self.lock = False


class Command:
    def __init__(self, playerID, command):
        # Client ID to receive the command
        self.playerID = playerID
        self.command = command


# Inbound Client Command
class QueueElement:
    def __init__(self, command):
        self.command = command


# Queue that will handle inbound Client commands
class Queue:
    def __init__(self):
        # Queue of QueueElements
        self.queue = []
        self.lock = False

    def insert(self, element):
        self.queue.append(element)

    def pop(self):
        return self.queue.pop(0)

    def is_empty(self):
        if len(self.queue) == 0:
            return True
        return False


class UdpServer:
    def __init__(self):
        """
        Create a new udp server
        """
        self.is_listening = True
        self.udp_host = ''
        # self.udp_port = int(input("Client UDP Port: "))
        self.udp_port = random.randint(5000, 5400)
        self.msg = '{"success": %(success)s, "message":"%(message)s"}'

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.udp_host, self.udp_port))
        self.sock.setblocking(False)
        self.sock.settimeout(5)

        # start_new_thread(self.run, ())

    def sendMessage(self, data):
        try:
            self.sock.sendto(data, (serverIP, 5666))
        except:
            print("Nao foi possivel enviar mensagem UDP para "+str((serverIP, 5666)))

    # Possui um servidor (objeto UdpServer) UDP que escuta infinitamente, em uma thread separada, mensagens do servidor
    def run(self):
        """
        Start udp server
        """
        print("Client UDP Server is listening")

        while self.is_listening:
            try:
                data, address = self.sock.recvfrom(1024)
                #print("Received: " + str(data.decode()))
            except socket.timeout:
                continue

        self.stop()

    def stop(self):
        """
        Stop server
        """
        self.sock.close()
