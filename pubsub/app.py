import asyncio
import json
import logging
import websockets

from uuid import uuid4
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class Action(Enum):
    initialize = 'initialize'
    register = 'register'
    subscribe = 'subscribe'
    refresh = 'refresh'

    @classmethod
    def to_json(cls):
        return { action.name:action.value for action in list(cls) }

labyrinths = {}
connections = {}

async def refresh():
    for connection in connections.values():
        await connection.send(json.dumps({
            'action': Action.refresh.value,
            'payload': {
                'actions': Action.to_json(),
                'labyrinths': labyrinths
            }
        }))


async def handle_register(websocket, websocket_id, path, payload):
    labyrinths[websocket_id] = payload

    await websocket.send(json.dumps({
        'action': Action.register.value,
        'payload': True
    }))

    await refresh()

message_handler = {
    Action.register.value: handle_register
}

async def hello(websocket, path):
    websocket_id = str(uuid4())
    connections[websocket_id] = websocket
    logger.info('Connecting to {}'.format(websocket.remote_address))

    await websocket.send(json.dumps({
        'action': Action.initialize.value,
        'payload': {
            'actions': Action.to_json(),
            'labyrinths': labyrinths
        }
    }))

    while True:
        try:
            message = json.loads(await websocket.recv())
            action = message['action']

            logger.info('Message from {}: {}'.format(websocket.remote_address, message))

            await message_handler[action](
                websocket,
                websocket_id,
                path,
                message['payload']
            )
        except websockets.ConnectionClosed:
            del connections[websocket_id]

            if websocket_id in labyrinths:
                del labyrinths[websocket_id]

            await refresh()

            break


start_server = websockets.serve(hello, 'localhost', 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
