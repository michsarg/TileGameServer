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


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('', 30020) 
sock.bind(server_address) 

# list of idnums
live_idnums = []
# key: idnum, value: names
clientdict = {}
# key: idnum, value: connection
connectiondict = {}

def client_handler(connection, address, idnum):
  #print('handling client {}'.format(address))
  #print('this thread is :{}'.format(threading.current_thread().getName()))

  host, port = address
  name = '{}:{}'.format(host, port)


  # Sent by the server to joining clients, to notify them of their idnum
  connection.send(tiles.MessageWelcome(idnum).pack())
  
  # Player join messages moved to server loop

  # Autostart when two players
  if (len(live_idnums) == 2):
    connection.send(tiles.MessageGameStart().pack())
  

  # Sent by the server to a single client, to add a new tile to that client's hand
  # refills the client's hand when theres an empty space (?)
  for _ in range(tiles.HAND_SIZE):
    tileid = tiles.get_random_tileid()
    connection.send(tiles.MessageAddTileToHand(tileid).pack())
  
  # Sent by the server to all clients to indicate that a new turn has started
  # need to iterate through player turns
  for x in connectiondict:
    connectiondict[x].send(tiles.MessagePlayerTurn(idnum).pack())
  #connection.send(tiles.MessagePlayerTurn(idnum).pack())
  

  # sets up a buffer for receiving chunks
  buffer = bytearray()

  # infinte loop for receiving 
  while True:
    chunk = connection.recv(4096)
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
            
            # send to indicate a new turn has started - why is it here??
            connection.send(tiles.MessagePlayerTurn(idnum).pack())



# handles new connections and distributes them
def start():
  sock.listen(5)
  print('listening on {}'.format(sock.getsockname()))

  while True:
    # handle each new connection independently
    connclient = sock.accept()
    connection, client_address = connclient

    # increment idnums according to number of players
    idnum = len(live_idnums)
    # add new player idnum to list of live idnums
    live_idnums.append(idnum)
    # update connectiondict
    connectiondict.update({idnum: connection})
    # update clientdict
    clientdict.update({idnum: client_address})

    host, port = client_address
    name = '{}:{}'.format(host, port)

    # inform all existing players that this player has joined
    # (this appears to NOT be sending)
    for x in connectiondict:
      # print('connection: {}'.format(connectiondict[x]))
      print('informing existing players this player has joined:')
      print('name:{} idnum:{}'.format(name, idnum))
      print('{}'.format(connectiondict[x]))
      connectiondict[x].send(tiles.MessagePlayerJoined(name, idnum).pack())

    # inform present player of past
    # (this appears to be working correctly)
    connection = connectiondict.get(idnum)
    for x in clientdict:
      print('x = {} cliendict.get(x)={}'.format(str(clientdict.get(x)), int(x)))
      connection.send(tiles.MessagePlayerJoined(str(clientdict.get(x)), int(x)).pack())

    thread = threading.Thread(target=client_handler, args=(connection, client_address, idnum))
    thread.start()

#main

print('Setting up new shared board')
board = tiles.Board()
print("[STARTING] server is starting")
#loop_thread = threading.Thread(target=server_loop, args=())
#loop_thread.start()
print('ayo')
start()