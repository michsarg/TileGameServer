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

live_idnums = []
client_data = {}
global_board = tiles.Board()



def add_client(connection, address):
  host, port = address
  name = '{}:{}'.format(host, port)


  idnum = len(live_idnums)
  live_idnums.append(idnum)
  print('idnum added: {}'.format(idnum))

  client_data[idnum] = {
  "connection" : connection,
  "address" : address,
  "host" : host,
  "port" : port,
  "name" : name
  }
  #send welcome message
  connection.send(tiles.MessageWelcome(idnum).pack())
  return idnum

def setup_game():

  for idnums in client_data: # will cycle 0 and 1
    
    print('TEST')
    print(client_data[idnums]["connection"])
    # Moved to add client
    # Message Welcome
    #client_data[idnums]["connection"].send(tiles.MessageWelcome(idnums).pack())
    
    
    # Message PlayerJoined
    client_data[idnums]["connection"].send(tiles.MessageWelcome(idnums).pack())

    # Message AddTileToHand
    for _ in range(tiles.HAND_SIZE):
      tileid = tiles.get_random_tileid()
      client_data[idnums]["connection"].send(tiles.MessageAddTileToHand(tileid).pack())
  
  for idnums in client_data: # will cycle 0 and 1
    # Message GameStart
    client_data[idnums]["connection"].send(tiles.MessageGameStart().pack())


def client_handler(connection, address):

  idnum = add_client(connection, address)
  print('idnum returned to client_handler: {}'.format(idnum))
  # start game when correct
  if len(live_idnums) == 2: 
    setup_game()
  else:
    listen()

  #setup player turns
    connection.send(tiles.MessagePlayerTurn(idnum).pack())
  
  ###

  #board created outside
  #board = tiles.Board()
  board = global_board

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


def listen():
  print('listening on {}'.format(sock.getsockname()))
  sock.listen(5)
  while True:
    connection, client_address = sock.accept()
    print('received connection from {}'.format(client_address))
    client_handler(connection, client_address)


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('', 30020)
sock.bind(server_address)
listen()




