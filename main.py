"""
Kafka Prometheus Monitoring - Main Script

This script demonstrates how to use all the components of the Kafka Prometheus
monitoring system together.
"""

import time
import logging
import argparse
import threading
from kafka_metrics_exporter import KafkaMetricsCollector
from kafka_consumer_lag_monitor import KafkaConsumerLagMonitor
from kafka_alert_publisher import KafkaAlertPublisher
from prometheus_client import start_http_server

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_metrics_exporter(args):
    """Run the Kafka metrics exporter"""
    logger.info("Starting Kafka metrics exporter")
    
    topics = args.topics.split(',') if args.topics else None
    consumer_groups = args.consumer_groups.split(',') if args.consumer_groups else None
    
    collector = KafkaMetricsCollector(
        bootstrap_servers=args.bootstrap_servers,
        topics=topics,
        consumer_groups=consumer_groups
    )
    
    start_http_server(args.metrics_port)
    logger.info(f"Serving Kafka metrics on :{args.metrics_port}")
    
    while True:
        try:
            collector.collect()
            logger.info("Metrics collected successfully")
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        time.sleep(args.metrics_interval)

def run_consumer_lag_monitor(args, alert_publisher):
    """Run the Kafka consumer lag monitor"""
    logger.info("Starting Kafka consumer lag monitor")
    
    consumer_groups = args.consumer_groups.split(',') if args.consumer_groups else None
    
    monitor = KafkaConsumerLagMonitor(
        bootstrap_servers=args.bootstrap_servers,
        consumer_groups=consumer_groups,
        alert_publisher=alert_publisher,
        warning_threshold=args.warning_threshold,
        critical_threshold=args.critical_threshold
    )
    
    start_http_server(args.lag_port)
    logger.info(f"Serving consumer lag metrics on :{args.lag_port}")
    
    while True:
        try:
            monitor.monitor_lag()
            logger.info("Consumer lag monitored successfully")
        except Exception as e:
            logger.error(f"Error monitoring consumer lag: {e}")
        
        time.sleep(args.lag_interval)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Kafka Prometheus Monitoring')
    
    parser.add_argument(
        '--bootstrap-servers',
        default='localhost:9092',
        help='Kafka bootstrap servers (default: localhost:9092)'
    )
    parser.add_argument(
        '--topics',
        help='Comma-separated list of topics to monitor'
    )
    parser.add_argument(
        '--consumer-groups',
        help='Comma-separated list of consumer groups to monitor'
    )
    
    parser.add_argument(
        '--metrics-port',
        type=int,
        default=9308,
        help='Port to expose metrics on (default: 9308)'
    )
    parser.add_argument(
        '--metrics-interval',
        type=int,
        default=30,
        help='Metrics collection interval in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--lag-port',
        type=int,
        default=9309,
        help='Port to expose consumer lag metrics on (default: 9309)'
    )
    parser.add_argument(
        '--lag-interval',
        type=int,
        default=60,
        help='Consumer lag monitoring interval in seconds (default: 60)'
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
        '--no-alerts',
        action='store_true',
        help='Disable sending alerts to Kafka'
    )
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    alert_publisher = None
    if not args.no_alerts:
        alert_publisher = KafkaAlertPublisher(
            bootstrap_servers=args.bootstrap_servers,
            alert_topic=args.alert_topic,
            metric_topic=args.metric_topic
        )
        logger.info("Alert publisher initialized")
    
    metrics_thread = threading.Thread(
        target=run_metrics_exporter,
        args=(args,),
        daemon=True
    )
    
    lag_thread = threading.Thread(
        target=run_consumer_lag_monitor,
        args=(args, alert_publisher),
        daemon=True
    )
    
    metrics_thread.start()
    lag_thread.start()
    
    logger.info("All components started")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        if alert_publisher:
            alert_publisher.close()
            logger.info("Alert publisher closed")

if __name__ == '__main__':
    main()
