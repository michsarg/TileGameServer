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
import random
import copy

REQ_PLAYERS = 4

live_idnums = [] # all connected clients
turn_order = [] # clients in this round & their order
client_data = {}
global_board = tiles.Board()
turn_idnum = 0
turn_index = 0
game_in_progress = False
eliminated = []


def add_client(connection, address):
  host, port = address
  name = '{}:{}'.format(host, port)

  idnum = len(live_idnums)
  live_idnums.append(idnum)
  
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
  global turn_order
  game_in_progress = True

  #select players to add to game
  turn_order = copy.deepcopy(live_idnums)
  turn_order[:REQ_PLAYERS]
  random.shuffle(turn_order)

  print('play order: {}'.format(turn_order))

  # send joining message
  for idnum_sent in turn_order:
    for idnum_receiver in client_data:
      if idnum_sent != idnum_receiver:
        idnum = idnum_sent
        name = client_data[idnum_sent]["name"]
        client_data[idnum_receiver]["connection"].send(tiles.MessagePlayerJoined(name, idnum).pack())

  # sent start message
  for idnums in client_data:
    client_data[idnums]["connection"].send(tiles.MessageGameStart().pack())

  # distribute first tiles to players
  for idnums in turn_order:
    print('sending tiles')
    for _ in range(tiles.HAND_SIZE):
      tileid = tiles.get_random_tileid()
      client_data[idnums]["connection"].send(tiles.MessageAddTileToHand(tileid).pack())


def progress_turn():
  #determine whos turn it is
  global live_idnums
  global turn_idnum # players will be notified this player can make next turn
  global turn_order # includes all players; those elinated are still in here
  global eliminated

  for index in range(len(turn_order)):
    # find the index that matches turn_idnum
    if turn_order[index] == turn_idnum:
      if (turn_order[(index+1)%len(turn_order)] not in eliminated):
        turn_idnum = turn_order[(index+1)%len(turn_order)]
        break
      elif (turn_order[(index+2)%len(turn_order)] not in eliminated):
        turn_idnum = turn_order[(index+2)%len(turn_order)]
        break
      elif (turn_order[(index+3)%len(turn_order)] not in eliminated):
        turn_idnum = turn_order[(index+3)%len(turn_order)]
        break
      elif (turn_order[(index+4)%len(turn_order)] not in eliminated):
        turn_idnum = turn_order[(index+4)%len(turn_order)]
        break

  for idnums in live_idnums:
    # Announce to every client it is this players turn
    client_data[idnums]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())
  

def game_over():
  pass

# this needs to be checked when a game ends
# and when a new player is added
def check_start_conditions():
  if (len(live_idnums) >= REQ_PLAYERS) & (game_in_progress == False):
    setup_game()
    run_game()
  else:
    #wait for more players if not enough are live
    listen()

def client_handler(connection, address):
  add_client(connection, address)
  check_start_conditions()


def update_and_notify():
  global client_data
  board = global_board
  global eliminated
  global live_idnums
  # update the board with token positions & determine any eliminations
  positionupdates, eliminated = board.do_player_movement(live_idnums)

  # print('eliminated')
  # print(eliminated)

  # notify all clients of new token positions on board
  for idnums in live_idnums: # change to only live actors
    for msg in positionupdates:
      client_data[idnums]["connection"].send(msg.pack())

  
  # notify all clients of eliminated players
  if len(eliminated) < 0:
    for idnums in live_idnums:
      for elim in eliminated:
        client_data[idnums]["connection"].send(tiles.MessagePlayerEliminated(elim).pack())
  #need to capture new elims here and send out messsage!!!!!
  #otherwise its nto registering??

  # check if a player has won the game
  if (len(turn_order)-len(eliminated)) == 1:
    print('GAME OVER BROS')

def run_game():

  global turn_order
  board = global_board
  global turn_idnum


  #start the first turn
  turn_idnum = turn_order[0]
  for idnums in client_data:
    client_data[idnums]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())

  buffer = bytearray()

  print('upon entering infinte loop, turn_idnum = {}'.format(turn_idnum))
  # Enter infinte loop for processing received chunks

  while True:

    # ignore messages if its not the players turn
    for idnums in client_data:
      if idnums == turn_idnum:
        chunk = client_data[idnums]["connection"].recv(4096)
        print('data received from {}'.format(idnums))
        if not chunk:
          print('client {} disconnected'.format(client_data[idnums]["address"]))
          return

    buffer.extend(chunk)

    while True:
      msg, consumed = tiles.read_message_from_bytearray(buffer)
      if not consumed:
        break

      buffer = buffer[consumed:]

      print('received message {}'.format(msg))

      # sent by the player to put a tile onto the board (all turns except second)
      if isinstance(msg, tiles.MessagePlaceTile):
        if board.set_tile(msg.x, msg.y, msg.tileid, msg.rotation, msg.idnum):

          # inform all clients of newly placed tile
          for idnums in live_idnums:
            client_data[idnums]["connection"].send(msg.pack())

          # update board and notify clients
          update_and_notify()

          # issue replacement tile to active player
          tileid = tiles.get_random_tileid()
          client_data[turn_idnum]["connection"].send(tiles.MessageAddTileToHand(tileid).pack())

          #initiate the next turn in the game
          progress_turn()

      # sent by the player in the second turn, to choose their token's starting path
      elif isinstance(msg, tiles.MessageMoveToken):
        if not board.have_player_position(msg.idnum):
          if board.set_player_start_position(msg.idnum, msg.x, msg.y, msg.position):
            
            # update board and notify clients
            update_and_notify()

            # start next turn
            progress_turn()


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




