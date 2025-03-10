import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Set
import websockets
from websockets.server import WebSocketServerProtocol

class WebsocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8001):
        self.host = host
        self.port = port
        self.clients: Dict[str, Set[WebSocketServerProtocol]] = {}
        self.message_queue = asyncio.Queue()
        self.running = False
        self.logger = logging.getLogger("WebsocketServer")
        
    async def start(self):
        self.running = True
        start_server = websockets.serve(self.handle_client, self.host, self.port)
        self.server = await start_server
        asyncio.create_task(self.process_message_queue())
        self.logger.info(f"WebSocket server started on {self.host}:{self.port}")
        
    async def stop(self):
        self.running = False
        if hasattr(self, 'server'):
            self.server.close()
            await self.server.wait_closed()
        self.logger.info("WebSocket server stopped")
        
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    action = data.get('action')
                    
                    if action == 'subscribe':
                        topic = data.get('topic')
                        if topic:
                            if topic not in self.clients:
                                self.clients[topic] = set()
                            self.clients[topic].add(websocket)
                            await websocket.send(json.dumps({
                                'action': 'subscribe',
                                'topic': topic,
                                'status': 'success'
                            }))
                            self.logger.info(f"Client subscribed to {topic}")
                    elif action == 'unsubscribe':
                        topic = data.get('topic')
                        if topic and topic in self.clients and websocket in self.clients[topic]:
                            self.clients[topic].remove(websocket)
                            await websocket.send(json.dumps({
                                'action': 'unsubscribe',
                                'topic': topic,
                                'status': 'success'
                            }))
                            self.logger.info(f"Client unsubscribed from {topic}")
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'error': 'Invalid JSON format'
                    }))
                except Exception as e:
                    await websocket.send(json.dumps({
                        'error': str(e)
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            for topic, clients in list(self.clients.items()):
                if websocket in clients:
                    clients.remove(websocket)
                    if not clients:
                        del self.clients[topic]
            
    async def process_message_queue(self):
        while self.running:
            try:
                message = await self.message_queue.get()
                topic = message.get('topic')
                
                if topic and topic in self.clients:
                    disconnected_clients = set()
                    
                    for client in self.clients[topic]:
                        try:
                            await client.send(json.dumps(message))
                        except websockets.exceptions.ConnectionClosed:
                            disconnected_clients.add(client)
                            
                    for client in disconnected_clients:
                        self.clients[topic].remove(client)
                        
                    if not self.clients[topic]:
                        del self.clients[topic]
                        
                self.message_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                
    async def broadcast(self, topic: str, data: Any):
        await self.message_queue.put({
            'topic': topic,
            'data': data
        })
        
    def broadcast_sync(self, topic: str, data: Any):
        asyncio.create_task(self.broadcast(topic, data)) 