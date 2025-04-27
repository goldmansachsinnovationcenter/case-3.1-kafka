# Kafka Monitoring with JMX Exporter and Micrometer

This directory contains configuration for monitoring Kafka using Prometheus JMX Exporter and Micrometer.

## JMX Exporter Setup

The JMX Exporter is a Java agent that exposes JMX metrics as Prometheus metrics. To use it with Kafka:

1. Download the JMX Exporter JAR file:
```bash
wget https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.17.2/jmx_prometheus_javaagent-0.17.2.jar -O jmx_prometheus_javaagent.jar
```

2. Add the following to your Kafka broker's startup script (e.g., `kafka-server-start.sh`):
```bash
export KAFKA_OPTS="$KAFKA_OPTS -javaagent:/path/to/jmx_prometheus_javaagent.jar=7071:/path/to/kafka-jmx-exporter.yml"
```

3. Restart your Kafka brokers to apply the changes.

The JMX Exporter will expose metrics on port 7071 at the `/metrics` endpoint.

## Micrometer Integration

For Java applications processing data through Kafka, you can use Micrometer for metrics collection:

1. Add Micrometer dependencies to your project:
```xml
<!-- Maven -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
    <version>1.10.5</version>
</dependency>
```

2. Configure Micrometer in your application:
```java
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.prometheus.PrometheusConfig;
import io.micrometer.prometheus.PrometheusMeterRegistry;

// Create a Prometheus registry
PrometheusMeterRegistry registry = new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);

// Register Kafka consumer metrics
registry.gauge("kafka.consumer.lag", 
               Tags.of("topic", "your-topic", "partition", "0"), 
               consumerLagValue);

// Expose metrics endpoint in your application
// For Spring Boot applications, this is done automatically
```

3. Create dedicated Kafka topics for monitoring:
```java
// Create a producer for the monitoring topic
KafkaProducer<String, String> monitoringProducer = new KafkaProducer<>(producerProps);

// Send alerts to a dedicated Kafka topic
public void sendAlert(String alertMessage) {
    ProducerRecord<String, String> record = 
        new ProducerRecord<>("system-alerts", alertMessage);
    monitoringProducer.send(record);
}

// Send metrics to a dedicated Kafka topic
public void sendMetric(String metricName, double value) {
    String metricJson = String.format("{\"name\":\"%s\",\"value\":%f,\"timestamp\":%d}", 
                                     metricName, value, System.currentTimeMillis());
    ProducerRecord<String, String> record = 
        new ProducerRecord<>("system-metrics", metricJson);
    monitoringProducer.send(record);
}
```

## Monitored Metrics

The `kafka-jmx-exporter.yml` configuration exposes the following critical metrics:

1. **Under-replicated Partitions**: `kafka_server_replicamanager_underreplicatedpartitions`
2. **Offline Replica Count**: `kafka_server_replicamanager_offlinereplicacount`
3. **Under Min ISR Partition Count**: `kafka_server_replicamanager_underminisrpartitioncount`
4. **Consumer Lag**: `kafka_server_fetcherlagmetrics_consumerlag`
5. **Request Metrics**: `kafka_network_requestmetrics_requestspersec_count`
6. **JVM Metrics**: Memory usage, GC activity, etc.

These metrics can be used to create alerts in Prometheus for detecting Kafka failures.
