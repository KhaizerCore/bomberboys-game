#!/usr/bin/env python3
# import sys

import time
from config import *
from _thread import *
import json
from datetime import datetime
import socket
import uuid
import random
import string
import mysql.connector

# Local Machine
serverIP = '0.0.0.0'
# serverIP = '192.168.15.1'

class TCPServer:
    def __init__(self):
        self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ServerSocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.host = serverIP
        self.port = 5555
        self.bufferSize = 4096
        self.ThreadCount = 0

        try:
            self.ServerSocket.bind((self.host, self.port))
        except socket.error as e:
            print(str(e))

        # PLAYER THING
        self.playerID = GUID()
        self.Lock = False
        self.players = []
        self.afk = []

        # Server Rooms
        self.rooms = Rooms(self)

        self.bombID = 0

        # Commands to be acquired by clients (to be replaced by another data structure)
        self.clientsCommands = ClientCommands()

        # Commands coming from clients
        self.queue = Queue()

        # UDP Server
        self.UDPServer = UdpServer(self)

    def acquire(self):
        while self.Lock:
            pass
        self.Lock = True

    def release(self):
        self.Lock = False

    def getData(self, datadecoded):
        if datadecoded[1] == "PLAYER_ID":
            return self.playerID.getGUID()

        if datadecoded[1] == "PLAYERS":
            data = []
            jsondata = {}
            for room in self.rooms.rooms:
                if room.guid == datadecoded[3]:
                    for player in room.players:
                        if player.id != datadecoded[2]:
                            data.append(player.__dict__)
                    jsondata = json.dumps(data)
            return jsondata

        if datadecoded[1] == "BOMB_ID":
            return self.bombID

        if datadecoded[1] == "COMMANDS":
            commands = []
            self.clientsCommands.acquire()
            for command in self.clientsCommands.commands:
                if command.playerID == datadecoded[2]:
                    commands.append(command.command)
                    self.clientsCommands.commands.remove(command)
            self.clientsCommands.release()
            if len(commands) > 0:
                print("RETORNA COMANDOS")
                print(commands)
            return json.dumps(commands)

        if datadecoded[1] == "AUTOJOIN":
            for player in self.players:
                if player.id == datadecoded[2]:
                    print(player.__dict__)
                    return self.rooms.autojoin(player)
            return -1

        if datadecoded[1] == "JOIN_SPECIFIC":
            #  2      3         4
            # name, password, playerGUID
            for player in self.players:
                if player.id == datadecoded[4]:
                    for room in self.rooms.rooms:
                        if room.name == datadecoded[2]:
                            if room.password == datadecoded[3]:
                                if room.available():
                                    room.insertPlayer(player)
                                    return room.guid
            return -1

        if datadecoded[1] == "ALL_ROOMS":
            all_rooms = []
            for room in self.rooms.rooms:
                if room.password:
                    room_type = 'private'
                else:
                    room_type = 'public'
                all_rooms.append([room.name, room_type, len(room.players), room.capacity])
            return json.dumps(all_rooms)

        return "err1"

    def setData(self, datadecoded):
        if datadecoded[1] == "PLAYER_POSITION":
            for room in self.rooms.rooms:
                if room.guid == datadecoded[6]:
                    for player in room.players:
                        if player.id == int(datadecoded[2]):
                            player.x = datadecoded[3]
                            player.y = datadecoded[4]
                            player.direction = datadecoded[5]

    def create(self, datadecoded, address, connection):

        if datadecoded[1] == "PLAYER":
            self.players.append(NetPlayer(datadecoded[2], datadecoded[3], datadecoded[5], datadecoded[4], address))
            print("Player created, GUID: " + str(datadecoded[5]))

        if datadecoded[1] == "BOMB":
            self.bombID += 1
            playerID = datadecoded[4]
            roomID = datadecoded[5]
            datadecoded.append(self.bombID)
            for room in self.rooms.rooms:
                if room.guid == roomID:
                    for player in room.players:
                        if player.id != playerID:
                            self.notifyCommand(player.id, datadecoded)

            print("Bomb created: " + str(self.bombID))
            connection.sendall(str(self.bombID).encode())

        if datadecoded[1] == "ROOM":
            roomName = datadecoded[2]
            password = datadecoded[3]
            capacity = datadecoded[4]
            created = self.rooms.createRoom(roomName, password, capacity)
            connection.sendall(json.dumps(created).encode())

    def delete(self, datadecoded):
        if datadecoded[1] == "PLAYER":
            print(str(datetime.now()) + " DELETE PLAYER REQUESTED")
            playerID = datadecoded[2]
            for player in self.players:
                if player.id == playerID:
                    keep_afk = True
                    self.removePlayer(player, keep_afk)

            print("Command objects: ")
            if len(self.clientsCommands.commands) > 0:
                print(self.clientsCommands.commands)

    # Database related request operations
    def db(self, datadecoded):
        # DATABASE CONNECTION
        database = mysql.connector.connect(
            host="localhost",
            user="gustavo",
            password="gustavo",
            database="dsgame"
        )

        mycursor = database.cursor()

        if datadecoded[1] == "LOGIN":
            username = datadecoded[2]
            password = datadecoded[3]
            print("\n___ REALIZANDO UMA CONSULTA NO BD ___")
            # DB Query
            mycursor.execute('SELECT * FROM USERACCOUNT USR WHERE USR.USERNAME = "' + username + '" AND USR.PASSWORD = "' + password + '"')
            myresult = mycursor.fetchall()

            print("login query")
            if len(myresult) > 0:
                mycursor.close()
                print("Login Success")
                ret = 1
                return str(ret).encode()
            else:
                mycursor.close()
                print("Falhou")
                ret = 0
                return str(ret).encode()

        if datadecoded[1] == "REGISTER":
            print("___ REALIZANDO O CADASTRO DE USUARIO NO BD ___")
            username = datadecoded[2]
            email = datadecoded[3]
            password = datadecoded[4]
            # DB Query
            mycursor.execute('SELECT * FROM USERACCOUNT USR WHERE USR.USERNAME = "' + username + '" OR USR.EMAIL = "'+ email +'"')
            if len(mycursor.fetchall())== 0:
                mycursor.execute('INSERT INTO USERACCOUNT(USERNAME,EMAIL,PASSWORD) VALUES ("' + username + '","' + email + '","' + password + '")')
                database.commit()
                print("register query")
                if mycursor.rowcount > 0:
                    mycursor.close()
                    print("Register Success")
                    ret = 1
                    return str(ret).encode()
                else:
                    mycursor.close()
                    print("O registro Falhou")
                    ret = 0
                    return str(ret).encode()
            else:
                mycursor.close()
                print("Falhou - Usuario/Email em uso")
                ret = -1
                return str(ret).encode()

    def notifyCommand(self, playerID, data):
        self.clientsCommands.acquire()
        self.clientsCommands.commands.append(Command(playerID, data))
        self.clientsCommands.release()

    def removePlayer(self, player, keep_afk):
        if player:
            for room in self.rooms.rooms:
                if room.guid == player.roomID:
                    # To notify all other players of the removal
                    command = "DELETE"
                    what = "PLAYER"
                    data = [command, what, player.id]
                    room.acquire()
                    for p in room.players:
                        if p.id != player.id:
                            self.acquire()
                            self.notifyCommand(p.id, data)
                            self.release()
                    room.release()

                    # In case of self.player becoming Clients to control out of the game things, change here.
                    if not keep_afk:
                        self.acquire()
                        print("Room size before delete: " + str(len(room.players)))
                        room.removePlayer(player)
                        print("Room size after delete: " + str(len(room.players)))
                        self.players.remove(player)
                        self.release()

    def stringfy(self, commands):
        command = ""
        ret_commands = []
        for letter in commands:
            command = str(command) + str(letter)
            if letter == "]":
                ret_commands.append(command)
                command = ""

        return ret_commands

    def analyzeData(self, connection, address, commands):
        commands = self.stringfy(commands)
        while commands:
            datadecoded = json.loads(commands.pop(0))
            if str(datadecoded[0]) == "GET":
                try:
                    connection.sendall(str(self.getData(datadecoded)).encode())
                except:
                    continue

            elif str(datadecoded[0]) == "SET":
                self.setData(datadecoded)

            elif str(datadecoded[0]) == "CREATE":
                self.create(datadecoded, address, connection)

            elif str(datadecoded[0]) == "DELETE":
                self.delete(datadecoded)

            elif str(datadecoded[0] == "DB"):
                try:
                    ret = self.db(datadecoded)
                    print("ret:", ret)
                    connection.sendall(ret)
                except:
                    continue

    def threaded_client(self, connection, address):
        # connection.send(str.encode('Welcome to the Server'))
        # connection.settimeout(10)
        while True:
            try:
                command = connection.recv(self.bufferSize)
                if not command:
                    print("not command")
                    for player in self.players:
                        if player.address == address:
                            keep_afk = False
                            self.removePlayer(player, keep_afk)
                            print("Client " + str(address) + " disconnected - null payload")
                    break
            # Client disconnected
            except:
                for player in self.players:
                    if player.address == address:
                        keep_afk = False
                        self.removePlayer(player, keep_afk)
                        print("Client "+str(address)+" disconnected - timeout")
                break

            if command:
                self.queue.insert(QueueElement(connection, address, command))

        print("Connection closing")
        connection.close()
        self.ThreadCount -= 1

    def serve_new_connections(self):
        print('Waiting for a Connection..')
        self.ServerSocket.listen(5)
        while True:
            conn, address = self.ServerSocket.accept()
            print('Connected to: ' + address[0] + ':' + str(address[1]))
            start_new_thread(self.threaded_client, (conn, address))
            self.ThreadCount += 1
            print('Thread Number: ' + str(self.ThreadCount))
        ServerSocket.close()

    def process_data(self):
        while True:
            t0 = datetime.now().microsecond
            if not self.queue.is_empty():
                firstElement = self.queue.pop()
                try:
                    if firstElement.command:
                        command = firstElement.command.decode()
                        self.analyzeData(firstElement.connection, firstElement.address, command)
                except UnicodeDecodeError:
                    continue


class UdpServer:
    def __init__(self, tcpserver):
        """
        Create a new udp server
        """
        self.is_listening = True
        self.udp_host = serverIP
        self.udp_port = 5666
        self.msg = '{"success": %(success)s, "message":"%(message)s"}'
        self.tcpserver = tcpserver
        # start_new_thread(self.run, ())

    def sendMessage(self, address):
        try:
            self.sock.sendto(str("Server message").encode(), address)
        except:
            print("Nao foi possivel enviar mensagem UDP para "+str(address))

    def run(self):
        """
        Start udp server
        """
        print("Server UDP Server is listening")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1)
        self.sock.bind((self.udp_host, self.udp_port))
        self.sock.setblocking(False)
        self.sock.settimeout(5)
        while self.is_listening:
            try:
                data, address = self.sock.recvfrom(1024)
                if data:
                    datadecoded = json.loads(data.decode())
                    if datadecoded[1] == "PLAYER_POSITION":
                        for player in self.tcpserver.players:
                            if player.id == int(datadecoded[2]):
                                player.x = datadecoded[3]
                                player.y = datadecoded[4]
                                player.direction = datadecoded[5]
            except socket.timeout:
                continue

            except KeyError:
                #print("Json from %s:%s is not valid" % address)
                continue
            except ValueError:
                #print("Message from %s:%s is not valid json string" % address)
                continue

        self.stop()

    def stop(self):
        """
        Stop server
        """
        self.sock.close()


class Rooms:
    def __init__(self, server):
        self.rooms = []
        self.Lock = False

        self.server = server
        self.guid = GUID()

        self.roomsLimit = 100
        self.playersInRoom = 4

        # self.createRoom(None, None, self.playersInRoom)

    def createRoom(self, name, password, capacity):
        guid = self.guid.getGUID()
        # last alteration here (and not....)
        if self.available() and not self.roomNameExists(name):
            self.acquire()
            self.rooms.append(Room(self.server, guid, name, password, capacity))
            self.release()
            return True
        else:
            print("Limite de Salas Atingido.")
            return False

    def removeRoom(self, room):
        self.acquire()
        self.rooms.remove(room)
        print("Room "+str(room.guid)+" removed")
        self.release()

    def available(self):
        if len(self.rooms) + 1 <= self.roomsLimit:
            return True
        return False

    def autojoin(self, player):
        for room in self.rooms:
            if room.available() and room.password == "":
                room.insertPlayer(player)
                return room.guid
        if self.createRoom(None, None, self.playersInRoom):
            return self.autojoin(player)

        print("Erro de conexao 1")
        # Servidor vazio ou cheio
        return -1

    def acquire(self):
        while self.Lock:
            pass
        self.Lock = True

    def release(self):
        self.Lock = False

    def roomNameExists(self, name):
        for room in self.rooms:
            if room.name == name:
                return True
        return False


class Room:
    def __init__(self, server, guid, name, password, capacity):
        self.server = server
        self.guid = guid
        if not name:
            self.name = str(self.get_random_string(8))
        else:
            self.name = name
        if not password:
            self.password = ""
        else:
            self.password = password
        self.capacity = capacity
        self.Lock = False
        self.players = []

        self.players_dict = []

        self.bombID = 0

        self.game_started = False

    def removePlayer(self, player):
        self.acquire()
        if self.players:
            self.players.remove(player)
            print("Player " + str(player.id) + " left the room " + str(self.guid))
        self.release()
        if len(self.players) == 0:
            self.server.rooms.removeRoom(self)

    def insertPlayer(self, player):
        self.acquire()
        if self.available():
            self.players.append(player)
            self.game_started = True
            player.roomID = self.guid
            print("Player "+str(player.id)+" joined the room "+str(self.guid))
        else:
            print("Room is Full! Try again later.")
        self.release()

    def available(self):
        if len(self.players) + 1 <= self.capacity:
            return True
        return False

    def getTotalClients(self):
        return len(self.players)

    def acquire(self):
        while self.Lock:
            pass
        self.Lock = True

    def release(self):
        self.Lock = False

    def get_random_string(self, length):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

class NetPlayer:
    def __init__(self, x, y, id, character, address):
        self.x = x * TILESIZE
        self.y = y * TILESIZE
        self.width = TILESIZE
        self.height = TILESIZE
        self.direction = "standing"
        self.character = character
        self.id = id
        self.roomID = None
        self.address = address
        self.spectating = False

# Commands to be sent to respective clients
class ClientCommands:
    def __init__(self):
        # Client ID to receive the command
        self.commands = []
        self.Lock = False

    def acquire(self):
        while self.Lock:
            pass
        self.Lock = True

    def release(self):
        self.Lock = False

# O comando em si, com o respectivo cliente destino
class Command:
    def __init__(self, playerID, command):
        # Client ID to receive the command
        self.playerID = playerID
        self.command = command


# Inbound Client Command
class QueueElement:
    def __init__(self, connection, address, command):
        self.connection = connection
        self.address = address
        self.command = command


# Queue that will handle inbound Client commands
class Queue:
    def __init__(self):
        # Queue of QueueElements
        self.queue = []
        self.lock = False

    def insert(self, element):
        self.acquire()
        self.queue.append(element)
        self.release()

    def pop(self):
        self.acquire()
        ret = self.queue.pop(0)
        self.release()
        return ret

    def is_empty(self):
        if len(self.queue) == 0:
            return True
        return False

    def acquire(self):
        while self.lock:
            pass
        self.lock = True

    def release(self):
        self.lock = False


# Responsável por gerar um ID unico para diversos casos de uso em objetos, a exemplo de Players
class GUID:
    def __init__(self):
        self.lock = False
        self.GUID = self.updateGUID()

    def updateGUID(self):
        while self.lock:
            pass
        self.lock = True
        self.GUID = uuid.uuid1().int
        self.lock = False
        return self.GUID

    def getGUID(self):
        while self.lock:
            pass
        return self.updateGUID()


server = TCPServer()
start_new_thread(server.process_data, ())
server.serve_new_connections()
