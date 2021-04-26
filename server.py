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
live_idnums = []

def client_handler(connection, address):
  
  host, port = address
  name = '{}:{}'.format(host, port)

  #need to increment idnums here 
  #idnum = port #was0
  idnum = len(live_idnums)
  live_idnums.append(idnum)

  print('idnum: {}'.format(idnum))


  connection.send(tiles.MessageWelcome(idnum).pack())
  connection.send(tiles.MessagePlayerJoined(name, idnum).pack())
  connection.send(tiles.MessageGameStart().pack())

  for _ in range(tiles.HAND_SIZE):
    tileid = tiles.get_random_tileid()
    connection.send(tiles.MessageAddTileToHand(tileid).pack())
  
  connection.send(tiles.MessagePlayerTurn(idnum).pack())
  
  board = tiles.Board()

  buffer = bytearray()


  while True:
    chunk = connection.recv(4096)
    if not chunk:
      print('client {} disconnected'.format(address))
      return

    buffer.extend(chunk)

    while True:
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

          # check for token movement
          positionupdates, eliminated = board.do_player_movement(live_idnums)

          for msg in positionupdates:
            connection.send(msg.pack())
          
          if idnum in eliminated:
            connection.send(tiles.MessagePlayerEliminated(idnum).pack())
            return

          # pickup a new tile
          tileid = tiles.get_random_tileid()
          connection.send(tiles.MessageAddTileToHand(tileid).pack())

          # start next turn
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
  sock.listen(5)
  print('listening on {}'.format(sock.getsockname()))
  while True: #! infinite loop
    # handle each new connection independently
    connection, client_address = sock.accept()
    #client_handler(connection, client_address)
    thread = threading.Thread(target=client_handler, args=(connection, client_address))
    thread.start()
    print('received connection from {}'.format(client_address))

print("[STARTING] server is starting")
start()