import json
import threading
from typing import Callable, Dict, Any
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class FederationBroker:
    """
    AiON Swarm Protocol (AiON-SP) Federation Broker.
    Manages cross-machine communication between independent AiON instances.
    Gracefully falls back to local in-memory queues if Redis is not available.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FederationBroker, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        self.redis_client = None
        self.pubsub = None
        self.subscriptions: Dict[str, Callable] = {}
        self.local_bus = []
        
        try:
            import redis
            # Attempt to connect to a Redis instance
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_client.ping()
            self.pubsub = self.redis_client.pubsub()
            logger.info("[FederationBroker] Connected to Redis. Cross-machine Federation ENABLED.")
            
            # Start background listener thread
            self.listener_thread = threading.Thread(target=self._listen_redis, daemon=True)
            self.listener_thread.start()
            
        except Exception as e:
            logger.warning(f"[FederationBroker] Redis not available ({e}). Federation running in LOCAL-ONLY mode.")
            self.redis_client = None
            
        self.initialized = True

    def _listen_redis(self):
        """Listens for federated messages on subscribed channels."""
        if not self.pubsub:
            return
            
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                channel = message['channel']
                if channel in self.subscriptions:
                    try:
                        data = json.loads(message['data'])
                        self.subscriptions[channel](data)
                    except Exception as e:
                        logger.error(f"[FederationBroker] Error processing message on {channel}: {e}")

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to a specific topic."""
        self.subscriptions[topic] = callback
        if self.redis_client:
            self.pubsub.subscribe(topic)
            logger.info(f"[FederationBroker] Subscribed to Federation Topic: {topic}")

    def publish(self, topic: str, message: Dict[str, Any]):
        """Publish a message to the federation bus."""
        if self.redis_client:
            try:
                self.redis_client.publish(topic, json.dumps(message))
                logger.info(f"[FederationBroker] Published message to {topic}")
            except Exception as e:
                logger.error(f"[FederationBroker] Failed to publish to Redis: {e}")
        else:
            # Fallback to local
            if topic in self.subscriptions:
                self.subscriptions[topic](message)
