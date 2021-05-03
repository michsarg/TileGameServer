# cits3002project

THINGS TO DO:

    configure delaying start of game until sufficient number of players have joined
    work out turn taking - currently non functional and sitting in client_handler
    implement event handling???


Notes:

In TCP, the client initiates a connection, and the server listens for and accepts a connection. Once connected, data can flow both ways.


client.py: 
    This module implements the game client. You do notneed to understand this code,but you may like to inspect it to understand how the client expects tointeract with the server
    you don't need to (but can) modify this code, but original must be submitted

server.py
    This module implements  a  basic  server  that  allows  a  single  client  to  play  asingle game with no other participants, and very little error checking.
    needs to be rewritten to:
        allow more players to join
        do error checks

tiles.py:
    This module defines essential constants and gameplay logic, which is shared by both the client and the server.
    contains game logic and constants
    must not be edited!


Tiers:
1- Enable Multiple Players
    implement basic server that can play a single game wiht two players
    trust they will only play valid cards on valid locations
    players can send msgs when its not their turn
    all connections need to be gast and stable

2- Scaling Up
    extend server so when a game finishes a new one autostarts with enough players
    server should be able to handle up to 4 player games
    randomly pick the 4 if mroe are connected
    other connected players can be spectators and watch game and get updates
    msgs from spectator and eliminatd players should be ignored

3- Connection Issues
    server must be able to handle unexpected network behaviour
    *   if a player exits durng game they should be eliminated then next player turn starts or if one left then they win
    *   server shoudl handle players attempting to join during the game by giving them updates but not letting them play turns

4- player issues
    make experience nicer for players tha tjoin partway through an existing game by helping them to catch up on the game state
    *  VARIOUS TASKS HERE
    ensure game continues for all players if a player goes afk
    *   VARIOUS TASKS HERE

::::::::GUIDE:::::
def client_handler(clients):

    # create dictionary of client data
    client_data = get_client_data(clients)

    # get a list of the idnums of players in the game
    live_idnums = list(client_data.keys())

    # send the game setup messages to all clients
    send_game_setup_messages(client_data, live_idnums)

    # add tiles to all clients hands
    add_initial_tiles_to_clients(get_connections(client_data))

    # creat the turn order
    turn_order = copy.deepcopy(live_idnums)
    random.shuffle(turn_order)
    print_turn_order(turn_order)

    # CREATE BOARD BEFORE TURN LOGIC