#!/usr/bin/env python3

# CITS3002 2021 Assignment
#
# This file implements a basic server that allows a single client to play a
# single game with no other participants, and very little error checking.
#
# Any other clients that connect during this time will need to wait for the
# first client's game to complete.
#
# Your task will be to write a new server that adds all connected clients into
# a pool of players. When enough players are available (two or more), the server
# will create a game with a random sample of those players (no more than
# tiles.PLAYER_LIMIT players will be in any one game). Players will take turns
# in an order determined by the server, continuing until the game is finished
# (there are less than two players remaining). When the game is finished, if
# there are enough players available the server will start a new game with a
# new selection of clients.

import socket
import sys
import tiles
import threading

# these disrupt settings in client which we cant edit
#PORT = 5050
#SERVER = socket.gethostbyname(socket.gethostname())
#address = (SERVER, PORT)

# create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# listen on all network interfaces
server_address = ('', 30020) #! specifies that the socket is reachable by any address the machine happens to have.
sock.bind(server_address) #! bind the socket to a host and port

# need to combine these in one data structure holding:
# name, idnum
# which is then held as an entry in a (?) list
live_idnums = []
threads = list()
#stores idnum and names
clientdict = {}

def client_handler(connection, address, idnum):
  print('handling client {}'.format(address))

  host, port = address
  name = '{}:{}'.format(host, port)

  x = clientdict.items()
  print(x)
  

  # Sent by the server to joining clients, to notify them of their idnum
  connection.send(tiles.MessageWelcome(idnum).pack())
  
  #Sent by the server to all clients, when a new game has started.
  if (len(live_idnums) == 1):
    # Sent by the server to all clients, when a new client joins.
    # This indicates the name and (unique) idnum for the new client.
    connection.send(tiles.MessagePlayerJoined(name, idnum).pack())
    connection.send(tiles.MessageGameStart().pack())
  else:
    # Sent by the server to all clients, when a new client joins.
    # This indicates the name and (unique) idnum for the new client.

    # for each client in live_idnums, send this!
    connection.send(tiles.MessagePlayerJoined(name, idnum).pack())

  # Sent by the server to a single client, to add a new tile to that client's hand
  # refills the client's hand when theres an empty space (?)
  for _ in range(tiles.HAND_SIZE):
    tileid = tiles.get_random_tileid()
    connection.send(tiles.MessageAddTileToHand(tileid).pack())
  
  # Sent by the server to all clients to indicate that a new turn has started
  # this needs to be alternated
  connection.send(tiles.MessagePlayerTurn(idnum).pack())
  

  # sets up a buffer for receiving chunks
  buffer = bytearray()

  # infinte loop for receiving 
  while True:
    chunk = connection.recv(4096) #checks correct chunk size
    if not chunk:
      print('client {} disconnected'.format(address))
      return

    buffer.extend(chunk)

    while True:
      # Attempts to read and unpack a single message from the beginning of the
      # provided bytearray. If successful, it returns (msg, number_of_bytes_consumed).
      # If unable to read a message (because there are insufficient bytes), it returns
      # (None, 0).
      msg, consumed = tiles.read_message_from_bytearray(buffer)
      if not consumed:
        break

      buffer = buffer[consumed:]

      print('received message {}'.format(msg))

      # sent by the player to put a tile onto the board (in all turns except
      # their second)
      if isinstance(msg, tiles.MessagePlaceTile):
        if board.set_tile(msg.x, msg.y, msg.tileid, msg.rotation, msg.idnum):
          # notify client that placement was successful
          connection.send(msg.pack())

          # For all of the player ids in the live_idnums list, this method will move
          # their player tokens if it is possible for them to move.
          positionupdates, eliminated = board.do_player_movement(live_idnums)

          for msg in positionupdates:
            connection.send(msg.pack())
          
          if idnum in eliminated:
            connection.send(tiles.MessagePlayerEliminated(idnum).pack())
            return

          # Sent by the server to a single client, to add a new tile to that client's hand.
          tileid = tiles.get_random_tileid()
          connection.send(tiles.MessageAddTileToHand(tileid).pack())

          # ent by the server to all clients to indicate that a new turn has started.
          connection.send(tiles.MessagePlayerTurn(idnum).pack())

      # sent by the player in the second turn, to choose their token's
      # starting path
      elif isinstance(msg, tiles.MessageMoveToken):
        if not board.have_player_position(msg.idnum):
          if board.set_player_start_position(msg.idnum, msg.x, msg.y, msg.position):
            # check for token movement
            positionupdates, eliminated = board.do_player_movement(live_idnums)

            for msg in positionupdates:
              connection.send(msg.pack())
            
            if idnum in eliminated:
              connection.send(tiles.MessagePlayerEliminated(idnum).pack())
              return
            
            # start next turn
            connection.send(tiles.MessagePlayerTurn(idnum).pack())



# handles new connections and distributes them
def start():
  sock.listen()
  print('listening on {}'.format(sock.getsockname()))

  while True: #! infinite loop
    # handle each new connection independently
    connection, client_address = sock.accept()

    # increment idnums according to number of players
    idnum = len(live_idnums)
    # add new player idnum to list of live idnums
    live_idnums.append(idnum)
    print('idnum: {}'.format(idnum))

    # NEED DATA STRUCTURE HERE TO RECORD idnum, connection, client_address
    # then can update relevant methods in handler to send to all, not just one

    #now passes idnum to new thread
    thread = threading.Thread(target=client_handler, args=(connection, client_address, idnum))
    print('starting new thread for {}'.format(client_address))
    threads.append(thread)

    # update clientdict
    host, port = client_address
    name = '{}:{}'.format(host, port)
    clientdict.update({idnum: name})

    thread.start()
    #print('received connection from {}'.format(client_address))


# MAIN
# sets up a new board

print('Setting up new shared board')
board = tiles.Board()
print("[STARTING] server is starting")
start()