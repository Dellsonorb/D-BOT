import json
import socket
import time
import uuid

DBOT_IP = "192.168.1.117"
DBOT_PORT = 6090
LOCAL_PORT = 16090

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", LOCAL_PORT))
sock.settimeout(8)

cmd = {
    "cmd_id": str(uuid.uuid4()),
    "action": "MOVE",
    "target": 5,
    "expect_ack": True,
}

print("send:", cmd)
sock.sendto(json.dumps(cmd).encode("utf-8"), (DBOT_IP, DBOT_PORT))

start = time.time()
while time.time() - start < 10:
    try:
        data, addr = sock.recvfrom(2048)
        msg = json.loads(data.decode("utf-8"))
        print("recv:", addr, msg)
        if msg.get("stage") in ("completed", "failed"):
            break
    except socket.timeout:
        print("timeout")
        break