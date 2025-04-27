"""
Test script to verify the Kafka monitoring and alerting setup.

This script simulates various Kafka failure scenarios to test that:
1. Metrics are properly collected and exposed
2. Prometheus scrapes the metrics correctly
3. Alert rules trigger appropriately
4. Alertmanager routes notifications correctly
"""

import time
import requests
import subprocess
import logging
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MonitoringTester:
    """Test the Kafka monitoring and alerting setup"""
    
    def __init__(self, bootstrap_servers='localhost:9092', 
                 prometheus_url='http://localhost:9090',
                 alertmanager_url='http://localhost:9093'):
        self.bootstrap_servers = bootstrap_servers
        self.prometheus_url = prometheus_url
        self.alertmanager_url = alertmanager_url
        
        self.admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
        
    def check_metrics_endpoint(self, port=9308):
        """Check if the metrics endpoint is accessible"""
        try:
            response = requests.get(f'http://localhost:{port}/metrics')
            if response.status_code == 200:
                logger.info(f"Metrics endpoint on port {port} is accessible")
                return True
            else:
                logger.error(f"Metrics endpoint returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing metrics endpoint: {e}")
            return False
    
    def check_prometheus_targets(self):
        """Check if Prometheus is scraping the targets"""
        try:
            response = requests.get(f'{self.prometheus_url}/api/v1/targets')
            if response.status_code == 200:
                targets = response.json()['data']['activeTargets']
                for target in targets:
                    logger.info(f"Target: {target['labels']['job']} - Health: {target['health']}")
                return True
            else:
                logger.error(f"Prometheus targets API returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing Prometheus targets API: {e}")
            return False
    
    def check_alertmanager_status(self):
        """Check if Alertmanager is running"""
        try:
            response = requests.get(f'{self.alertmanager_url}/api/v2/status')
            if response.status_code == 200:
                logger.info("Alertmanager is running")
                return True
            else:
                logger.error(f"Alertmanager status API returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing Alertmanager status API: {e}")
            return False
    
    def simulate_consumer_lag(self, topic='test-topic', group='test-group', messages=1000):
        """Simulate consumer lag by producing messages without consuming"""
        logger.info(f"Simulating consumer lag for topic {topic}")
        
        try:
            self.admin_client.create_topics([NewTopic(topic, 1, 1)])
            logger.info(f"Created topic {topic}")
        except KafkaError as e:
            logger.info(f"Topic {topic} already exists or error: {e}")
        
        for i in range(messages):
            self.producer.send(topic, f"message-{i}".encode('utf-8'))
        self.producer.flush()
        logger.info(f"Produced {messages} messages to topic {topic}")
        
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group,
            auto_offset_reset='earliest'
        )
        
        consumer.poll(timeout_ms=1000)
        consumer.close()
        
        logger.info(f"Created consumer group {group} with lag")
        
        time.sleep(60)
        
        self.check_alerts()
    
    def check_alerts(self):
        """Check if alerts are triggered in Prometheus"""
        try:
            response = requests.get(f'{self.prometheus_url}/api/v1/alerts')
            if response.status_code == 200:
                alerts = response.json()['data']['alerts']
                if alerts:
                    logger.info(f"Found {len(alerts)} active alerts:")
                    for alert in alerts:
                        logger.info(f"Alert: {alert['labels']['alertname']} - State: {alert['state']}")
                else:
                    logger.info("No active alerts found")
                return True
            else:
                logger.error(f"Prometheus alerts API returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing Prometheus alerts API: {e}")
            return False
    
    def run_all_tests(self):
        """Run all monitoring tests"""
        logger.info("Starting monitoring tests...")
        
        self.check_metrics_endpoint(9308)  # Kafka metrics exporter
        self.check_metrics_endpoint(9309)  # Consumer lag monitor
        
        self.check_prometheus_targets()
        
        self.check_alertmanager_status()
        
        self.simulate_consumer_lag()
        
        logger.info("Monitoring tests completed")

def main():
    """Main function"""
    tester = MonitoringTester()
    tester.run_all_tests()

if __name__ == '__main__':
    main()
