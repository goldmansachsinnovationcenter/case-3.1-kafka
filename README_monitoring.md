# Kafka Monitoring Solution with Prometheus

This directory contains a comprehensive monitoring solution for Apache Kafka using Prometheus and Alertmanager. The solution provides real-time metrics collection, alerting, and visualization capabilities for Kafka clusters.

## Code Structure

### Python Scripts

- **`kafka_metrics_exporter.py`**: Main metrics collection script that connects to Kafka brokers and exposes metrics in Prometheus format
  - Collects broker metrics, topic metrics, and consumer group metrics
  - Exposes metrics on port 9308 by default
  - Uses the Kafka Admin API to gather cluster information

- **`kafka_consumer_lag_monitor.py`**: Specialized script for monitoring consumer lag
  - Tracks consumer group lag across all topics and partitions
  - Sends alerts when lag exceeds configurable thresholds
  - Exposes metrics on port 9309 by default

- **`kafka_alert_publisher.py`**: Utility script for publishing alerts to Kafka topics
  - Used by other components to send alerts to dedicated monitoring topics
  - Supports different alert types and severity levels

- **`main.py`**: Entry point that orchestrates all monitoring components
  - Starts both the metrics exporter and consumer lag monitor
  - Handles graceful shutdown and resource cleanup

### Configuration Files

- **`config/prometheus/`**: Prometheus configuration
  - `prometheus.yml`: Main Prometheus configuration with scrape targets
  - `kafka_alerts.yml`: Alert rules for common Kafka failure scenarios

- **`config/alertmanager/`**: Alertmanager configuration
  - `alertmanager.yml`: Alert routing and notification configuration
  - Supports email, Slack, and PagerDuty notifications

- **`config/kafka-exporter/`**: JMX exporter configuration
  - `kafka-jmx-exporter.yml`: JMX metrics configuration for Kafka brokers
  - `README.md`: Documentation for JMX exporter setup

### Docker Setup

- **`Dockerfile.exporter`**: Docker image for Python monitoring scripts
  - Based on Python 3.9-slim
  - Includes all required dependencies

- **`docker-compose.yml`**: Complete monitoring stack deployment
  - Kafka and Zookeeper services
  - Metrics exporters
  - Prometheus and Alertmanager
  - Grafana for visualization

### Tests

- **`test_monitoring_setup.py`**: Integration test script
  - Verifies metrics collection and alerting functionality
  - Simulates failure scenarios to test alert rules

- **`tests/monitoring/test_kafka_metrics_exporter.py`**: Unit tests
  - Tests for the metrics collection logic
  - Mocks Kafka API responses for testing

### Dependencies

- **`monitoring-requirements.txt`**: Python dependencies
  - kafka-python: Kafka client library
  - prometheus-client: Prometheus metrics library
  - pytest: Testing framework

## Alert Types

The monitoring solution detects and alerts on the following Kafka failure scenarios:

1. **Under-replicated Partitions**: Indicates potential data loss risk
2. **Offline Partitions**: Critical issue affecting availability
3. **Consumer Lag**: Detects processing delays
4. **Topic Partition Count Changes**: Monitors topology changes
5. **Message Rate Anomalies**: Detects unusual traffic patterns
6. **JVM Memory Issues**: Monitors broker health

## Usage

1. Deploy using Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Access monitoring interfaces:
   - Prometheus: http://localhost:9090
   - Alertmanager: http://localhost:9093
   - Grafana: http://localhost:3000

3. Run tests:
   ```bash
   python test_monitoring_setup.py
   ```

## Architecture

The monitoring solution follows a modular architecture:

1. **Metrics Collection**: Python scripts collect metrics from Kafka
2. **Metrics Exposition**: Metrics are exposed in Prometheus format
3. **Scraping**: Prometheus scrapes metrics at regular intervals
4. **Alerting**: Alert rules evaluate metrics and trigger alerts
5. **Notification**: Alertmanager routes alerts to appropriate channels
6. **Visualization**: Grafana provides dashboards for metrics

This architecture ensures scalability, reliability, and ease of maintenance for monitoring Kafka deployments.
