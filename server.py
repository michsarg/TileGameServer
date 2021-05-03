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

REQ_PLAYERS = 2

live_idnums = []
player_idnums = []
client_data = {}
global_board = tiles.Board()
turn_idnum = 0
game_in_progress = False

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
  game_in_progress = True

  #select players to add to game
  chosen_idnums = copy.deepcopy(live_idnums)
  random.shuffle(chosen_idnums)
  for chosen in range(0, (REQ_PLAYERS)):
    player_idnums.append(chosen_idnums[chosen])

  print('play order: {}'.format(player_idnums))
  # NEED TO GO THROUGH ALL CODE TO IMPLEMENT PLAYER ID NUMS
  # IF IT IS RELATED TO PLAYING THE NAME, REPLACE WITH PLAYER IDNUMS
  # IF IT IS RELATED TO SENDING UPDATES ABOUT THE GAME, ALL IDNUMS SHOULD GET THAT

  # send joining message
  for idnum_sender in player_idnums:
    for idnum_receiver in client_data:
      if idnum_sender != idnum_receiver:
        idnum = idnum_sender
        name = client_data[idnum_sender]["name"]
        client_data[idnum_receiver]["connection"].send(tiles.MessagePlayerJoined(name, idnum).pack())

  # sent start message
  for idnums in client_data: # will cycle 0 and 1
    # Message GameStart
    client_data[idnums]["connection"].send(tiles.MessageGameStart().pack())

  # distribute first tiles to players
  for idnums in player_idnums:
    print('sending tiles')
    for _ in range(tiles.HAND_SIZE):
      tileid = tiles.get_random_tileid()
      client_data[idnums]["connection"].send(tiles.MessageAddTileToHand(tileid).pack())


def progress_turn():
  #determine whos turn it is
  global live_idnums
  global turn_idnum 


  #protects against loss of order with player elimination
  for index in range(0, len(player_idnums)):
    if player_idnums[index] == turn_idnum:
      turn_idnum = player_idnums[(index+1)%len(player_idnums)]
      break
  #this is not progressing
  print('turn_idnum: {}'.format(turn_idnum))

  for idnums in client_data:
    # Announce to every client it is this players turn
    client_data[idnums]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())
  

def game_over():
  # remove wininer, end game, attempt restart
  #
  # game_in_progress = False
  #
  # if live_idnums >= REQ_PLAYERS:
  #   randomly select  
  #
  # check_start_conditions()
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
  board = global_board
  # update the board with token positions & determine any eliminations
  positionupdates, eliminated = board.do_player_movement(live_idnums)

  # notify all clients of new token positions on board
  for idnums in client_data:
    for msg in positionupdates:
      client_data[idnums]["connection"].send(msg.pack())
  
  # notify all clients of elminiated players
  for idnum_elim in client_data:
    if idnum_elim in eliminated:
      for idnums in client_data:
        client_data[idnums]["connection"].send(tiles.MessagePlayerEliminated(idnum_elim).pack())
        return
  
  # update player_idnums to remove eliminated
  for idnum_elim in eliminated:
    if idnum_elim in player_idnums:
      player_idnums.remove(idnum_elim)
  
  # check if a player has won the game
  if player_idnums == 1:
    print('GAME OVER BROS')

def run_game():
  board = global_board
  
  #start the first turn
  turn_id = player_idnums[0]
  progress_turn()

  buffer = bytearray()
  #infinte loop begins for processing received chunks
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
          for idnums in client_data:
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




