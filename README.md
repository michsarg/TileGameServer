# CITS3002 Networking: Game Server Project 2021 S1

---

## Description of Modules

### client.py: 
This module implements the game client. You do notneed to understand this code,but you may like to inspect it to understand how the client expects tointeract with the server. You don't need to (but can) modify this code, but original must be submitted.

### server.py
This module implements  a  basic  server  that  allows  a  single  client  to  play  asingle game with no other participants, and very little error checking. This needs to be rewritten to:
* allow more players to join
* do error checks

### tiles.py:
This module defines essential constants and gameplay logic, which is shared by both the client and the server. It contains game logic and constants and must not be edited!

---

## Marking Tiers

### 1) Enable Multiple Players
* implement basic server that can play a single game with two players
* trust they will only play valid cards on valid locations
* players can send msgs when its not their turn
* all connections need to be gast and stable

### 2) Scaling Up
* extend server so when a game finishes a new one autostarts with enough players
* server should be able to handle up to 4 player games
* randomly pick the 4 if mroe are connected
* other connected players can be spectators and watch game and get updates
* msgs from spectator and eliminatd players should be ignored

### 3) Connection Issues
* server must be able to handle unexpected network behaviour
    * if a player exits durng game they should be eliminated then next player turn starts or if one left then they win
    * server should handle players attempting to join during the game by giving them updates but not letting them play turns

### 4) Player issues
* make experience nicer for players that join partway through an existing game by helping them to catch up on the game state
* ensure game continues for all players if a player goes afk
