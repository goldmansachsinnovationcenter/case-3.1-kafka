# Offline Partitions Runbook

## Alert Description
This alert triggers when Kafka has partitions that are offline and unavailable for producers or consumers. Offline partitions result in data unavailability and can cause application failures.

## Potential Causes
- All replicas for a partition are down
- Leader election failure
- Corrupted log files
- Zookeeper connection issues
- Controller broker failure
- Severe resource exhaustion

## Diagnostic Steps
1. Check for offline partitions:
   ```bash
   kafka-topics.sh --bootstrap-server <kafka-bootstrap-servers> --describe | grep -i "Leader: -"
   ```

2. Check controller logs:
   ```bash
   grep -i controller /var/log/kafka/server.log | tail -n 100
   ```

3. Check Zookeeper status:
   ```bash
   echo stat | nc localhost 2181
   ```

4. Verify broker status:
   ```bash
   kafka-broker-api-versions.sh --bootstrap-server <kafka-bootstrap-servers>
   ```

## Resolution Steps
1. If Zookeeper is down or unreachable:
   - Check Zookeeper service status:
     ```bash
     systemctl status zookeeper
     ```
   - Restart Zookeeper if needed:
     ```bash
     systemctl restart zookeeper
     ```
   - Wait for Kafka to reconnect and elect leaders

2. If broker with partition leaders is down:
   - Restart the affected broker:
     ```bash
     systemctl restart kafka
     ```
   - Check if leaders are re-elected:
     ```bash
     kafka-topics.sh --bootstrap-server <kafka-bootstrap-servers> --describe
     ```

3. If log files are corrupted:
   - Check log directories for errors:
     ```bash
     ls -la /var/lib/kafka/data/
     ```
   - Consider moving corrupted segments and restarting the broker:
     ```bash
     mkdir -p /tmp/kafka-corrupted
     mv /var/lib/kafka/data/topic-partition/segment.log /tmp/kafka-corrupted/
     systemctl restart kafka
     ```
   
4. For persistent issues, trigger a controller reassignment:
   ```bash
   # First check the current controller
   zookeeper-shell.sh localhost:2181 get /controller
   
   # Then trigger a reassignment by removing the controller znode
   zookeeper-shell.sh localhost:2181 delete /controller
   ```

## Prevention
1. Ensure multiple broker redundancy:
   - Use a replication factor of at least 3 for critical topics
   - Distribute brokers across multiple racks/availability zones

2. Implement proper monitoring for:
   - Zookeeper connectivity
   - Controller broker health
   - Log directory disk space and health

3. Configure appropriate timeouts:
   ```properties
   # In server.properties
   zookeeper.session.timeout.ms=18000
   zookeeper.connection.timeout.ms=10000
   ```

4. Regularly test broker failure scenarios:
   - Simulate broker failures in non-production environments
   - Document recovery procedures
