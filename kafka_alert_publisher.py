"""
Kafka Alert Publisher

This script publishes alerts to dedicated Kafka topics for operational monitoring.
It can be used to send system alerts and processing metrics to separate Kafka topics.
"""

import json
import logging
import argparse
import time
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KafkaAlertPublisher:
    """
    Publisher for sending alerts and metrics to dedicated Kafka topics.
    """
    def __init__(self, bootstrap_servers, alert_topic='system-alerts', metric_topic='system-metrics'):
        """
        Initialize the Kafka alert publisher.
        
        Args:
            bootstrap_servers (str): Kafka bootstrap servers
            alert_topic (str): Topic for system alerts
            metric_topic (str): Topic for system metrics
        """
        self.bootstrap_servers = bootstrap_servers
        self.alert_topic = alert_topic
        self.metric_topic = metric_topic
        
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        
        logger.info(f"Initialized Kafka alert publisher with bootstrap servers: {bootstrap_servers}")
        logger.info(f"Alert topic: {alert_topic}")
        logger.info(f"Metric topic: {metric_topic}")
    
    def send_alert(self, alert_type, message, severity='warning', metadata=None):
        """
        Send an alert to the alert topic.
        
        Args:
            alert_type (str): Type of alert (e.g., 'broker_down', 'under_replicated')
            message (str): Alert message
            severity (str): Alert severity (info, warning, error, critical)
            metadata (dict): Additional metadata for the alert
        
        Returns:
            Future: Kafka future for the send operation
        """
        metadata = metadata or {}
        
        alert = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata
        }
        
        logger.info(f"Sending alert: {alert}")
        
        return self.producer.send(
            self.alert_topic,
            key=alert_type,
            value=alert
        ).add_callback(self._on_send_success).add_errback(self._on_send_error)
    
    def send_metric(self, metric_name, value, tags=None):
        """
        Send a metric to the metric topic.
        
        Args:
            metric_name (str): Name of the metric
            value (float): Metric value
            tags (dict): Tags for the metric
        
        Returns:
            Future: Kafka future for the send operation
        """
        tags = tags or {}
        
        metric = {
            'name': metric_name,
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'tags': tags
        }
        
        logger.info(f"Sending metric: {metric}")
        
        return self.producer.send(
            self.metric_topic,
            key=metric_name,
            value=metric
        ).add_callback(self._on_send_success).add_errback(self._on_send_error)
    
    def _on_send_success(self, record_metadata):
        """Callback for successful send"""
        logger.debug(f"Message sent to {record_metadata.topic} [{record_metadata.partition}] @ {record_metadata.offset}")
    
    def _on_send_error(self, exc):
        """Callback for send error"""
        logger.error(f"Error sending message: {exc}")
    
    def close(self):
        """Close the producer"""
        self.producer.close()
        logger.info("Kafka producer closed")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Kafka Alert Publisher')
    parser.add_argument(
        '--bootstrap-servers',
        default='localhost:9092',
        help='Kafka bootstrap servers (default: localhost:9092)'
    )
    parser.add_argument(
        '--alert-topic',
        default='system-alerts',
        help='Topic for system alerts (default: system-alerts)'
    )
    parser.add_argument(
        '--metric-topic',
        default='system-metrics',
        help='Topic for system metrics (default: system-metrics)'
    )
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    publisher = KafkaAlertPublisher(
        bootstrap_servers=args.bootstrap_servers,
        alert_topic=args.alert_topic,
        metric_topic=args.metric_topic
    )
    
    try:
        publisher.send_alert(
            alert_type='example_alert',
            message='This is an example alert',
            severity='info',
            metadata={'source': 'example'}
        )
        
        publisher.send_metric(
            metric_name='example_metric',
            value=42.0,
            tags={'source': 'example'}
        )
        
        publisher.producer.flush()
        
        logger.info("Example messages sent successfully")
    finally:
        publisher.close()

if __name__ == '__main__':
    main()
