"""
Unit tests for the Kafka Metrics Exporter
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from prometheus_client import REGISTRY

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_metrics_exporter import KafkaMetricsCollector

class TestKafkaMetricsCollector(unittest.TestCase):
    """Test cases for the KafkaMetricsCollector class"""
    
    def tearDown(self):
        """Clean up after each test"""
        collectors = list(REGISTRY._collector_to_names.keys())
        for collector in collectors:
            REGISTRY.unregister(collector)
    
    @patch('kafka_metrics_exporter.KafkaAdminClient')
    @patch('kafka_metrics_exporter.KafkaConsumer')
    def setUp(self, mock_consumer, mock_admin):
        """Set up test fixtures"""
        self.mock_admin = mock_admin.return_value
        self.mock_consumer = mock_consumer.return_value
        
        self.mock_admin.list_topics.return_value = ['test-topic-1', 'test-topic-2']
        
        topic_metadata = [
            {
                'topic': 'test-topic-1',
                'partitions': [
                    {
                        'id': 0,
                        'leader': 1,
                        'replicas': [1, 2, 3],
                        'isr': [1, 2, 3]
                    },
                    {
                        'id': 1,
                        'leader': 2,
                        'replicas': [1, 2, 3],
                        'isr': [1, 2]  # Under-replicated
                    }
                ]
            }
        ]
        self.mock_admin.describe_topics.return_value = topic_metadata
        
        self.mock_admin.list_consumer_groups.return_value = [('test-group', 'consumer')]
        
        self.collector = KafkaMetricsCollector(bootstrap_servers='localhost:9092')
        
        self.collector.under_replicated_partitions = MagicMock()
        self.collector.offline_partitions = MagicMock()
        self.collector.consumer_lag = MagicMock()
        self.collector.topic_partition_count = MagicMock()
        self.collector.topic_message_count = MagicMock()
    
    def test_collect_topic_metrics(self):
        """Test collecting topic metrics"""
        self.collector.collect_topic_metrics()
        
        self.mock_admin.list_topics.assert_called_once()
        self.assertEqual(self.mock_admin.describe_topics.call_count, 2)
        self.mock_admin.describe_topics.assert_any_call(['test-topic-1'])
        self.mock_admin.describe_topics.assert_any_call(['test-topic-2'])
        
        self.collector.topic_partition_count.labels.assert_any_call(topic='test-topic-1')
        self.collector.topic_partition_count.labels().set.assert_any_call(2)
        
        self.collector.under_replicated_partitions.labels.assert_any_call(topic='test-topic-1')
        self.collector.under_replicated_partitions.labels().set.assert_any_call(1)
        
        self.collector.offline_partitions.labels.assert_any_call(topic='test-topic-1')
        self.collector.offline_partitions.labels().set.assert_any_call(0)
    
    @patch('kafka_metrics_exporter.KafkaConsumer')
    def test_collect_consumer_metrics(self, mock_consumer_class):
        """Test collecting consumer metrics"""
        from kafka.structs import TopicPartition
        tp = TopicPartition('test-topic-1', 0)
        
        class MockOffset:
            def __init__(self, offset):
                self.offset = offset
        
        offsets = {tp: MockOffset(100)}
        self.mock_admin.list_consumer_group_offsets.return_value = offsets
        
        mock_consumer_instance = mock_consumer_class.return_value
        mock_consumer_instance.position.return_value = 150  # End offset
        
        self.collector.collect_consumer_metrics()
        
        self.mock_admin.list_consumer_groups.assert_called_once()
        self.mock_admin.list_consumer_group_offsets.assert_called_once_with('test-group')
        
        mock_consumer_instance.assign.assert_called_once()
        mock_consumer_instance.seek_to_end.assert_called_once()
        mock_consumer_instance.position.assert_called_once()
        
        self.collector.consumer_lag.labels.assert_called_with(
            group='test-group', 
            topic='test-topic-1', 
            partition='0'
        )
        self.collector.consumer_lag.labels().set.assert_called_with(50)  # 150 - 100 = 50
    
    def test_collect(self):
        """Test the main collect method"""
        self.collector.collect_topic_metrics = MagicMock()
        self.collector.collect_consumer_metrics = MagicMock()
        self.collector.collect_broker_metrics = MagicMock()
        
        self.collector.collect()
        
        self.collector.collect_topic_metrics.assert_called_once()
        self.collector.collect_consumer_metrics.assert_called_once()
        self.collector.collect_broker_metrics.assert_called_once()

if __name__ == '__main__':
    unittest.main()
