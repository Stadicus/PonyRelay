#!/usr/bin/python3
"""--------------------------------------------------
ponyrelayd: monitors directory for gammu sms files
            and broadcasts a Bitcoin transaction 
            following the Pony Direct structure
------------------------------------------------"""

import os, sys, time, sys, json, subprocess
import argparse, logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

# global config
pattern = 'x'

# global data
sms_spool = []
sms_index = []

class MyEventHandler(PatternMatchingEventHandler):
  global args
  patterns=["*.*"]

  def process(self, event):
    """
    event.event_type
      'modified' | 'created' | 'moved' | 'deleted'
    event.is_directory
      True | False
    event.src_path
      path/to/observed/file
    """
    sms_index_row = []
    self.patterns = args["pattern"].replace("qr","*")

    if event.is_directory:
      return

    logging.info("  FILE: processing " + event.src_path)

    # SUB: Read File
    with open(event.src_path, 'r') as file_source:
      file_string = file_source.read()
      try:
        # get sender mobile#
        sms_sender = event.src_path.split("_")[3]
        sms = json.loads(file_string)
      except:
        logging.error(" FILE: unable to parse: " + event.src_path)
        shutil.move(event.src_path, args["faileddir"]+"InputErr_"+os.path.basename(event.src_path))
        return

    sms_payload_id = sms['i']	if 'i' in sms else ''
    sms_sequence = sms['c']	if 'i' in sms else ''
    sms_tx = sms['t']		if 'i' in sms else ''

    sms_spool_row = [sms_sender, sms_payload_id, sms_sequence, sms_tx, event.src_path]

    # sms_spool exists and the current sms (mobile#, payload, sequence) already exists
    if sms_spool and any([s for s in sms_spool if s[0] == sms_sender and s[1] == sms_payload_id and s[2] == sms_sequence]):
      logging.info("  SPOOL: duplicate file: (sender, payload_id, seq, tx) " + ', '.join(str(e) for e in sms_spool_row))
      return
    else:
      logging.debug(" SPOOL: new file added: (sender, payload_id, seq, tx) " + ', '.join(str(e) for e in sms_spool_row))
      sms_spool.append(sms_spool_row)

    # if hash present get index entry
    if 'h' in sms and not any([i for i in sms_index if i[0] == sms_sender and i[1] == sms_payload_id]):
      sms_hash = sms['h']
      sms_segments = sms['s']	if 's' in sms else ''
      sms_network = sms['n']	if 'n' in sms else ''

      sms_index_row = [sms_sender, sms_payload_id, sms_segments, sms_hash, sms_network]
      sms_index.append(sms_index_row)
      logging.debug(" INDEX: new transaction: (sender, payload_id, segm, hash, net) " + ', '.join(str(e) for e in sms_index_row))

    send_tx(sms_sender, sms_payload_id)

  def on_modified(self, event):
    self.process(event)


def send_tx(sender, payload_id):
  # check if all sms segments available
  try:
    sms_segments_req = [i for i in sms_index if i[0] == sender and i[1] == payload_id][0][2]
  except Exception as e:
    logging.debug(" SPOOL: transaction index not yet present.")
    return

  # Check if expected number of sms is present
  sms_segments_in_spool = len([s for s in sms_spool if s[0] == sender and s[1] == payload_id])
  logging.debug(" SPOOL: sms segments in spool: " + str(sms_segments_in_spool) +"/"+ str(sms_segments_req))

  if sms_segments_in_spool == sms_segments_req:
    logging.debug(" SPOOL: all sms segments present.")
    sms_index_row = [i for i in sms_index if i[0] == sender and i[1] == payload_id]
    logging.debug(" INDEX: data loaded: (sender, payload_id, segm, hash, net) " + ', '.join(str(e) for e in sms_index_row))

    # Load spool rows for this transaction, sort by sequence, concatenate raw transaction
    sms_spool_sorted = sorted([s for s in sms_spool if s[0] == sender and s[1] == payload_id],key=lambda x: (x[2]))
    logging.debug(" TX: spool rows loaded: " + str(len(sms_spool_sorted)))
    tx_raw = '';

    for r in sms_spool_sorted:
      tx_raw += r[3]
    logging.debug(" TX: rawtransaction: " + tx_raw)

    # verify SMS hash with TXID from bitcoin-cli decoderawtransaction
    try:
      tx_decode_obj = subprocess.run(['bitcoin-cli', 'decoderawtransaction', tx_raw], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      tx_decode = json.loads(tx_decode_obj.stdout.decode("utf-8"))
      tx_txid = tx_decode['txid']
    except:
      logging.error(" TX: could not call bitcoin-cli:" + tx_decode_obj.stdout.decode("utf-8"))

    if sms_index_row[0][3] == tx_txid:
      logging.debug(" TX: sms hash & txid match: " + tx_txid)
    else:
      logging.error(" TX: sms hash & txid DO NOT match: " + sms_index_row[0][3] +" / "+ tx_txid)
      return;

    # broadcast transaction
    tx_send_obj = subprocess.run(['bitcoin-cli', 'sendrawtransaction', tx_raw], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if tx_send_obj.returncode:
      logging.error(" TX: sendrawtransaction failed, " + tx_send_obj.stderr.decode("utf-8").replace("\n", " "))
      file_dest = args["faileddir"] + "err" + str(tx_send_obj.returncode) + "_"
      #return
    else:
      logging.info("  TX: sendrawtransaction success, tx id: " + tx_send_obj.stdout.decode("utf-8"))
      file_dest = args["archivedir"]

    # Move files to archive and remove from sms_spool
    for s in sms_spool_sorted:
      filename = os.path.basename(s[4])
      shutil.move(s[4], file_dest + filename)
      logging.debug(" FILE: moved " + s[4] +" --> "+ file_dest + filename)
      sms_spool.remove(s)
      logging.debug(" SPOOL: file removed, remaining: " + str(len(sms_spool)))

def config():
  global pattern, datadir
  parser = argparse.ArgumentParser(description='relay Pony Express Bitcoin SMS transactions', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument('--datadir', default=str(Path.home())+'/.ponyrelay/', help='base data directory')
  parser.add_argument('--watchdir', default=str(Path.home())+'/.ponyrelay/in/', help='directory monitored for incoming sms')
  parser.add_argument('--archivedir', default=str(Path.home())+'/.ponyrelay/archive/', help='targed directory for successful transactions')
  parser.add_argument('--faileddir', default=str(Path.home())+'/.ponyrelay/failed/', help='target directory for failed transactions')
  parser.add_argument('--pattern', default='*.*', help='file pattern to monitor in watchdir')
  parser.add_argument('--loglevel', default='INFO', help='detail level of log file', choices=['INFO','DEBUG'])
  parser.add_argument('--logfile', default=str(Path.home())+'/.ponyrelay/ponyrelay.log', help='location of log file')

  args_obj = parser.parse_args()
  args = vars(args_obj)
  return args


if __name__ == '__main__':
  print("Pony Relay version 0.1-alpha started.")
  args = config()

  logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=args['logfile'], level=logging.INFO)
  logging.info("  Pony Relay version 0.1-alpha started.")
  logging.info("  -------------------------------------")
  logging.debug(" CONFIG: data dir:    "+ args['datadir'])
  logging.debug(" CONFIG: watch dir:   "+ args['watchdir'])
  logging.debug(" CONFIG: archive dir: "+ args['archivedir'])
  logging.debug(" CONFIG: failed dir:  "+ args['faileddir'])
  logging.debug(" CONFIG: file pattern: "+ args['pattern'])
  logging.debug(" CONFIG: log level: "+ args['loglevel'] +" into "+ args['logfile'])

  # start monitoring directory for incoming sms
  observer = Observer()
  observer.schedule(MyEventHandler(), args['watchdir'])
  observer.start()

  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    observer.stop()

  observer.join()
