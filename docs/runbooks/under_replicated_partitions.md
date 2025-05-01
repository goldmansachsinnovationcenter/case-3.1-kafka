# Under-replicated Partitions Runbook

## Alert Description
This alert triggers when Kafka has partitions that are not fully replicated across the number of brokers specified by the replication factor. Under-replicated partitions indicate a potential risk of data loss if additional brokers fail.

## Potential Causes
- Broker(s) down or unreachable
- Network issues between brokers
- Overloaded brokers (CPU, memory, disk I/O)
- Insufficient disk space on brokers
- Kafka process running out of memory

## Diagnostic Steps
1. Check broker status:
   ```bash
   kafka-topics.sh --bootstrap-server <kafka-bootstrap-servers> --describe --under-replicated
   ```

2. Identify affected topics and brokers:
   ```bash
   kafka-topics.sh --bootstrap-server <kafka-bootstrap-servers> --describe | grep -i under-replicated
   ```

3. Check broker logs for errors:
   ```bash
   tail -n 1000 /var/log/kafka/server.log | grep ERROR
   ```

4. Check broker resource utilization:
   ```bash
   # CPU and memory usage
   top -bn1 | grep java
   
   # Disk usage
   df -h
   ```

## Resolution Steps
1. For offline brokers:
   - Check if the Kafka service is running:
     ```bash
     systemctl status kafka
     ```
   - Restart the offline broker if needed:
     ```bash
     systemctl restart kafka
     ```

2. For resource issues:
   - If disk space is low, clean up old logs:
     ```bash
     # Find and delete old log files
     find /var/log/kafka -name "*.log.*" -mtime +7 -delete
     ```
   - If broker is CPU/memory constrained:
     - Adjust Kafka heap settings in /etc/kafka/jvm.options
     - Restart the broker after changes:
       ```bash
       systemctl restart kafka
       ```

3. For network issues:
   - Check network connectivity between brokers:
     ```bash
     ping <broker-ip>
     telnet <broker-ip> 9092
     ```
   - Fix network issues or firewall rules as needed

4. If issue persists, consider increasing the replication timeout:
   ```bash
   # Edit server.properties
   replica.lag.time.max.ms=30000
   ```

## Prevention
1. Implement proper monitoring for:
   - Disk space utilization (alert at 80% usage)
   - Broker CPU and memory usage
   - Network connectivity between brokers

2. Configure appropriate log retention:
   ```properties
   # In server.properties
   log.retention.hours=168  # 7 days
   log.segment.bytes=1073741824  # 1GB
   ```

3. Scale your cluster appropriately:
   - Add more brokers if consistently at high utilization
   - Increase replication factor for critical topics
