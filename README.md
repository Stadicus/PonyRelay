# PonyRelay
#### Relay PonyDirect SMS transaction to the Bitcoin network

Aimed at improving Bitcoins resiliency, PonyRelay is a simple Python application that acts as a bridge between SMS texts and the Bitcoin peer-to-peer network. 
It watches a folder for incoming Bitcoin transactions, delivered by text messages originating from the [PonyDirect](https://github.com/MuleTools/PonyDirect) mobile app.
A Bitcoin transaction is transmitted using multiple text messaages, so this PonyRelay reconstructs and validates the transaction and broadcasts it through a running Bitcoin node.

### Development
This is the very first version 0.1-alpha. It works on my machine. Feel free to play with it. Improvement proposals are welcome!

Todo-List:
- [ ] cleanup routine (drop out orphaned files and spool entries after some time)
- [ ] add support for SMS API gateway, using web hooks
- [ ] support for low-cost GSM module on Raspberry Pi
- [ ] whitelist, blacklist senders, with option to send confirmation text message
- [ ] use Bitcoin Core JSON-RPC directly
- [ ] add tests
- [ ] make a guide :-)

### Requiremens
- `bitcoin-cli` connected to a Bitcon node needs to be present
- Mobile broadband modem (eg. usb-stick), configured with `gammu-smsd` to receive text messages

### Installation
From GitHub
```
$ sudo apt install git 
$ git clone https://github.com/Stadicus/ponyrelay
$ cd ponyrelay
$ pip install logging
$ pip install -r requirements.txt
$ ./ponyrelay.py
```

Use `./ponyrelay.py --help` for information about command line arguments.
