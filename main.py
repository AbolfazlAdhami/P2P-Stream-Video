import argparse
from peer import Peer

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--target-ip", required=True)
parser.add_argument("--target-port", type=int, required=True)

args = parser.parse_args()

Peer(args.port, args.target_ip, args.target_port).start()
