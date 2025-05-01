"""
Kafka Metrics Exporter for Prometheus

This script collects metrics from Kafka brokers and exposes them via HTTP
for Prometheus to scrape. It uses the kafka-python library to interact with
Kafka and the Prometheus client library to expose metrics.
"""

import time
import logging
import argparse
import json
from prometheus_client import start_http_server, Gauge, Counter
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
from kafka import KafkaConsumer, KafkaAdminClient
from kafka.admin import ConfigResource, ConfigResourceType
from kafka.errors import KafkaError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KafkaMetricsCollector:
    """
    Collector for Kafka metrics that implements the Prometheus collector interface.
    """
    def __init__(self, bootstrap_servers, topics=None, consumer_groups=None):
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics or []
        self.consumer_groups = consumer_groups or []
        
        self.admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
        
        self.under_replicated_partitions = Gauge(
            'kafka_under_replicated_partitions', 
            'Number of under-replicated partitions',
            ['topic']
        )
        self.offline_partitions = Gauge(
            'kafka_offline_partitions',
            'Number of offline partitions',
            ['topic']
        )
        self.consumer_lag = Gauge(
            'kafka_consumer_lag',
            'Consumer lag in messages',
            ['group', 'topic', 'partition']
        )
        self.topic_partition_count = Gauge(
            'kafka_topic_partition_count',
            'Number of partitions for a topic',
            ['topic']
        )
        self.topic_message_count = Counter(
            'kafka_topic_message_count',
            'Number of messages in a topic',
            ['topic']
        )
        
    def collect_topic_metrics(self):
        """Collect metrics for Kafka topics"""
        try:
            topics = self.admin_client.list_topics()
            
            for topic in topics:
                if self.topics and topic not in self.topics:
                    continue
                
                topic_partitions = self.admin_client.describe_topics([topic])
                
                partition_count = len(topic_partitions[0]['partitions'])
                self.topic_partition_count.labels(topic=topic).set(partition_count)
                
                under_replicated = 0
                for partition in topic_partitions[0]['partitions']:
                    if len(partition['replicas']) > len(partition['isr']):
                        under_replicated += 1
                
                self.under_replicated_partitions.labels(topic=topic).set(under_replicated)
                
                offline = 0
                for partition in topic_partitions[0]['partitions']:
                    if partition['leader'] == -1:
                        offline += 1
                
                self.offline_partitions.labels(topic=topic).set(offline)
                
        except KafkaError as e:
            logger.error(f"Error collecting topic metrics: {e}")
    
    def collect_consumer_metrics(self):
        """Collect metrics for Kafka consumer groups"""
        try:
            consumer_groups = self.admin_client.list_consumer_groups()
            
            for group in [g[0] for g in consumer_groups]:
                if self.consumer_groups and group not in self.consumer_groups:
                    continue
                
                offsets = self.admin_client.list_consumer_group_offsets(group)
                
                for tp, offset in offsets.items():
                    topic, partition = tp.topic, tp.partition
                    
                    consumer = KafkaConsumer(
                        bootstrap_servers=self.bootstrap_servers,
                        auto_offset_reset='latest',
                        group_id=None
                    )
                    
                    consumer.assign([tp])
                    consumer.seek_to_end(tp)
                    end_offset = consumer.position(tp)
                    consumer.close()
                    
                    lag = end_offset - offset.offset
                    self.consumer_lag.labels(
                        group=group, 
                        topic=topic, 
                        partition=str(partition)
                    ).set(lag)
                    
        except KafkaError as e:
            logger.error(f"Error collecting consumer metrics: {e}")
    
    def collect_broker_metrics(self):
        """Collect metrics for Kafka brokers"""
        try:
            brokers = self.admin_client.describe_cluster()
            
            logger.info(f"Found {len(brokers['brokers'])} brokers")
            
        except KafkaError as e:
            logger.error(f"Error collecting broker metrics: {e}")
    
    def collect(self):
        """Collect all Kafka metrics"""
        self.collect_topic_metrics()
        self.collect_consumer_metrics()
        self.collect_broker_metrics()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Kafka Metrics Exporter for Prometheus')
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
        '--port',
        type=int,
        default=9308,
        help='Port to expose metrics on (default: 9308)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Metrics collection interval in seconds (default: 30)'
    )
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    topics = args.topics.split(',') if args.topics else None
    consumer_groups = args.consumer_groups.split(',') if args.consumer_groups else None
    
    collector = KafkaMetricsCollector(
        bootstrap_servers=args.bootstrap_servers,
        topics=topics,
        consumer_groups=consumer_groups
    )
    
    start_http_server(args.port)
    logger.info(f"Serving Kafka metrics on :{args.port}")
    
    while True:
        try:
            collector.collect()
            logger.info("Metrics collected successfully")
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        time.sleep(args.interval)

if __name__ == '__main__':
    main()
