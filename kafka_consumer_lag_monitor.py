"""
Kafka Consumer Lag Monitor

This script specifically monitors consumer lag for Kafka consumer groups
and can send alerts when lag exceeds thresholds.
"""

import time
import logging
import argparse
import json
from prometheus_client import start_http_server, Gauge
from kafka import KafkaConsumer, KafkaAdminClient, TopicPartition
from kafka.errors import KafkaError

from kafka_alert_publisher import KafkaAlertPublisher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KafkaConsumerLagMonitor:
    """
    Monitor for Kafka consumer lag with alerting capabilities.
    """
    def __init__(self, bootstrap_servers, consumer_groups=None, 
                 alert_publisher=None, warning_threshold=1000, 
                 critical_threshold=10000):
        """
        Initialize the Kafka consumer lag monitor.
        
        Args:
            bootstrap_servers (str): Kafka bootstrap servers
            consumer_groups (list): List of consumer groups to monitor
            alert_publisher (KafkaAlertPublisher): Alert publisher instance
            warning_threshold (int): Warning threshold for consumer lag
            critical_threshold (int): Critical threshold for consumer lag
        """
        self.bootstrap_servers = bootstrap_servers
        self.consumer_groups = consumer_groups or []
        self.alert_publisher = alert_publisher
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        
        self.admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
        
        self.consumer_lag = Gauge(
            'kafka_consumer_lag',
            'Consumer lag in messages',
            ['group', 'topic', 'partition']
        )
        
        logger.info(f"Initialized Kafka consumer lag monitor with bootstrap servers: {bootstrap_servers}")
        logger.info(f"Warning threshold: {warning_threshold}")
        logger.info(f"Critical threshold: {critical_threshold}")
    
    def get_consumer_groups(self):
        """
        Get all consumer groups if none specified.
        
        Returns:
            list: List of consumer group IDs
        """
        if self.consumer_groups:
            return self.consumer_groups
        
        try:
            consumer_groups = self.admin_client.list_consumer_groups()
            return [g[0] for g in consumer_groups]
        except KafkaError as e:
            logger.error(f"Error getting consumer groups: {e}")
            return []
    
    def get_consumer_lag(self, group):
        """
        Get consumer lag for a consumer group.
        
        Args:
            group (str): Consumer group ID
        
        Returns:
            dict: Dictionary of topic-partition to lag
        """
        try:
            offsets = self.admin_client.list_consumer_group_offsets(group)
            
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                auto_offset_reset='latest',
                group_id=None
            )
            
            lag_by_tp = {}
            
            for tp, offset in offsets.items():
                consumer.assign([tp])
                consumer.seek_to_end(tp)
                end_offset = consumer.position(tp)
                
                lag = end_offset - offset.offset
                lag_by_tp[tp] = lag
                
                self.consumer_lag.labels(
                    group=group, 
                    topic=tp.topic, 
                    partition=str(tp.partition)
                ).set(lag)
                
                if self.alert_publisher and lag >= self.critical_threshold:
                    self._send_alert(group, tp, lag, 'critical')
                elif self.alert_publisher and lag >= self.warning_threshold:
                    self._send_alert(group, tp, lag, 'warning')
            
            consumer.close()
            return lag_by_tp
        
        except KafkaError as e:
            logger.error(f"Error getting consumer lag for group {group}: {e}")
            return {}
    
    def _send_alert(self, group, tp, lag, severity):
        """
        Send an alert for high consumer lag.
        
        Args:
            group (str): Consumer group ID
            tp (TopicPartition): Topic partition
            lag (int): Consumer lag
            severity (str): Alert severity
        """
        if not self.alert_publisher:
            return
        
        alert_type = 'consumer_lag'
        message = f"Consumer lag for group {group} on {tp.topic}[{tp.partition}] is {lag} messages"
        metadata = {
            'group': group,
            'topic': tp.topic,
            'partition': tp.partition,
            'lag': lag,
            'threshold': self.critical_threshold if severity == 'critical' else self.warning_threshold
        }
        
        self.alert_publisher.send_alert(
            alert_type=alert_type,
            message=message,
            severity=severity,
            metadata=metadata
        )
    
    def monitor_lag(self):
        """
        Monitor consumer lag for all groups.
        
        Returns:
            dict: Dictionary of group to lag by topic-partition
        """
        groups = self.get_consumer_groups()
        lag_by_group = {}
        
        for group in groups:
            lag_by_tp = self.get_consumer_lag(group)
            lag_by_group[group] = lag_by_tp
            
            if lag_by_tp:
                max_lag = max(lag_by_tp.values())
                logger.info(f"Group {group}: Max lag = {max_lag} messages")
            else:
                logger.info(f"Group {group}: No lag information available")
        
        return lag_by_group

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Kafka Consumer Lag Monitor')
    parser.add_argument(
        '--bootstrap-servers',
        default='localhost:9092',
        help='Kafka bootstrap servers (default: localhost:9092)'
    )
    parser.add_argument(
        '--consumer-groups',
        help='Comma-separated list of consumer groups to monitor'
    )
    parser.add_argument(
        '--warning-threshold',
        type=int,
        default=1000,
        help='Warning threshold for consumer lag (default: 1000)'
    )
    parser.add_argument(
        '--critical-threshold',
        type=int,
        default=10000,
        help='Critical threshold for consumer lag (default: 10000)'
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
    parser.add_argument(
        '--port',
        type=int,
        default=9309,
        help='Port to expose metrics on (default: 9309)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Monitoring interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--no-alerts',
        action='store_true',
        help='Disable sending alerts to Kafka'
    )
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    consumer_groups = args.consumer_groups.split(',') if args.consumer_groups else None
    
    alert_publisher = None
    if not args.no_alerts:
        alert_publisher = KafkaAlertPublisher(
            bootstrap_servers=args.bootstrap_servers,
            alert_topic=args.alert_topic,
            metric_topic=args.metric_topic
        )
    
    monitor = KafkaConsumerLagMonitor(
        bootstrap_servers=args.bootstrap_servers,
        consumer_groups=consumer_groups,
        alert_publisher=alert_publisher,
        warning_threshold=args.warning_threshold,
        critical_threshold=args.critical_threshold
    )
    
    start_http_server(args.port)
    logger.info(f"Serving consumer lag metrics on :{args.port}")
    
    try:
        while True:
            monitor.monitor_lag()
            logger.info(f"Sleeping for {args.interval} seconds")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        if alert_publisher:
            alert_publisher.close()

if __name__ == '__main__':
    main()
