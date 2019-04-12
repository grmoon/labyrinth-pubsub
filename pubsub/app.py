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
    connect_to_labyrinth = 'connect_to_labyrinth'
    get_labyrinth = 'get_labyrinth'
    deliver_labyrinth = 'deliver_labyrinth'

    @classmethod
    def to_json(cls):
        return { action.name:action.value for action in list(cls) }

labyrinths = {}
connections = {}

async def refresh():
    logger.info('Refreshing connections.')

    for connection in connections.values():
        await connection.send(json.dumps({
            'action': Action.refresh.value,
            'payload': {
                'actions': Action.to_json(),
                'labyrinths': labyrinths
            }
        }))

async def handle_deliver_labyrinth(websocket, websocket_id, path, payload):
    labyrinth_destination_id = payload['for']
    labyrinth = payload['labyrinth']

    logger.info('Delivering labyrinth {} to websocket {}.'.format(websocket_id, labyrinth_destination_id))

    if labyrinth_destination_id in connections:
        labyrinth_destination = connections[labyrinth_destination_id]

        await labyrinth_destination.send(json.dumps({
            'action': Action.deliver_labyrinth.value,
            'payload': {
                'labyrinth': labyrinth
            }
        }))

async def handle_connect_to_labyrinth(websocket, websocket_id, path, payload):
    labyrinth_id = payload['labyrinth_id']

    logger.info('Connecting websocket {} to labyrinth {}.'.format(websocket_id, labyrinth_id))

    if labyrinth_id in connections:
        labyrinth_owner = connections[labyrinth_id]

        await labyrinth_owner.send(json.dumps({
            'action': Action.get_labyrinth.value,
            'payload': {
                'for': websocket_id
            }
        }))

async def handle_register(websocket, websocket_id, path, payload):
    logger.info('Registering labyrinth {}.'.format(websocket_id))
    labyrinths[websocket_id] = payload

    await websocket.send(json.dumps({
        'action': Action.register.value,
        'payload': {
            'success': True
        }
    }))

    await refresh()

message_handler = {
    Action.register.value: handle_register,
    Action.connect_to_labyrinth.value: handle_connect_to_labyrinth,
    Action.deliver_labyrinth.value: handle_deliver_labyrinth,
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


start_server = websockets.serve(hello, '0.0.0.0', 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
