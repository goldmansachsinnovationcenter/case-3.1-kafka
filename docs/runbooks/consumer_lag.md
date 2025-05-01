# Consumer Lag Runbook

## Alert Description
This alert triggers when consumer groups fall behind processing messages, resulting in a growing backlog. Consumer lag indicates processing bottlenecks that may lead to delayed data processing or out-of-memory conditions.

## Potential Causes
- Consumer instance failures or crashes
- Increased message production rate
- Slower message processing (code issues)
- Network issues between consumers and brokers
- Resource constraints (CPU, memory) on consumer hosts
- Consumer rebalancing events

## Diagnostic Steps
1. Check current consumer lag:
   ```bash
   kafka-consumer-groups.sh --bootstrap-server <kafka-bootstrap-servers> --describe --group <group-id>
   ```

2. Monitor consumer group members:
   ```bash
   kafka-consumer-groups.sh --bootstrap-server <kafka-bootstrap-servers> --describe --group <group-id> --state
   ```

3. Check consumer application logs for errors or slowdowns

4. Monitor resource usage on consumer hosts:
   ```bash
   top -bn1 | grep java
   ```

5. Check production rate to see if it has increased:
   ```bash
   # Using Kafka metrics
   kafka-run-class.sh kafka.tools.GetOffsetShell --broker-list <kafka-bootstrap-servers> --topic <topic> --time -1
   # Run this command twice with an interval to calculate the rate
   ```

## Resolution Steps
1. For consumer instance failures:
   - Restart failed consumer instances
   - Check application logs for root cause of failures
   - Fix any application errors causing crashes

2. For processing bottlenecks:
   - Scale out by adding more consumer instances:
     ```bash
     # Ensure topic has enough partitions to support parallelism
     kafka-topics.sh --bootstrap-server <kafka-bootstrap-servers> --alter --topic <topic> --partitions <new-partition-count>
     
     # Then start additional consumer instances
     ```
   - Optimize consumer configuration:
     ```properties
     # Increase fetch size
     fetch.max.bytes=52428800  # 50MB
     max.partition.fetch.bytes=1048576  # 1MB
     
     # Tune processing batches
     max.poll.records=500
     ```

3. For resource constraints:
   - Allocate more CPU/memory to consumer applications
   - Consider upgrading hardware for consumer hosts
   - Optimize JVM settings if using Java consumers:
     ```
     export KAFKA_HEAP_OPTS="-Xms1G -Xmx2G"
     ```

4. For temporary lag spikes:
   - If lag is due to temporary production rate increase, monitor until consumers catch up
   - If needed, pause other non-critical processing to prioritize catch-up

## Prevention
1. Implement proper consumer scaling strategy:
   - Ensure sufficient partitioning for parallelism
   - Implement auto-scaling based on lag metrics

2. Configure appropriate monitoring thresholds:
   ```
   # Warning threshold (configurable in kafka_consumer_lag_monitor.py)
   warning_threshold=1000
   
   # Critical threshold
   critical_threshold=10000
   ```

3. Optimize consumer configuration for performance:
   ```properties
   # Tune consumer throughput
   fetch.min.bytes=1024
   fetch.max.wait.ms=500
   ```

4. Implement backpressure mechanisms in producers if needed
