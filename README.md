# OpenModding bot

This bot is made to help users with modding, here you can save all the link that
are usefull for your device, like roms, kernels, guides and much more..
I thinked about this 'cause I was tired of searching everyday for new roms, so
I've made this, all the links, all the roms, all in one place.
Now it's easy, no?

Btw be thankful with your admins that will update the rom list in this bot!

Example of my bot for kenzo users: [KenzoModding_bot](http://t.me/KenzoModding_bot)

Use [this channel](https://t.me/tostabots) to get notified when there's a new commit

## Getting Started

### Prerequisites

Python 2.7, and requirements.txt 

Add your [BotFather](http://t.me/BotFather) token here:![alt tag](http://i.imgur.com/ufcz8ic.png)

### Start it

```python bot.py```

## Setup the bot

Add new roms in the db(that will be created after the /start command).
First of all add the title of your links collection(like nougat or kernel).
But remember: you need to add ```_roms``` after the name (only in devices).

Example:
![alt tag](http://i.imgur.com/funCBEs.png)

Then set ```privs -2 ``` in the db for the admins, only who have privs -2 can
use admin commands (that are listed on ```/adminhelp```).
Example:
![alt tag](http://i.imgur.com/n58pmUx.png)

Now you're ready!


### Available commands

```
/kb or /keyboard | Brings the normal keyboard up.
/nkb or /nokeyboard | Brings the annoying keyboard down!
/menu | Shows the inline menù! It's cool!
/send | to send a message to all the users that have started the bot
/add |  to add something (you need to set the "collection" name first)
```
You can see the other commands with:
```/help``` or ```/adminhelp```(that's for admins obv).

## Contributors
Thanks to [Kyraminol](https://github.com/Kyraminol) that helped me A LOT.
