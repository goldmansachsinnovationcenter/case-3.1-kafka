# Topic Partition Count Changes Runbook

## Alert Description
This alert triggers when the number of partitions for a topic changes unexpectedly. Partition count changes can impact message ordering, consumer rebalancing, and overall stream processing topology.

## Potential Causes
- Manual topic reconfiguration
- Automated scripts changing topic configuration
- Misconfigured admin tools
- Unauthorized access to Kafka administration
- Bug in applications that dynamically create or modify topics

## Diagnostic Steps
1. Check topic partition configuration:
   ```bash
   kafka-topics.sh --bootstrap-server <kafka-bootstrap-servers> --describe --topic <topic>
   ```

2. Review recent administrative actions:
   ```bash
   # Check Kafka server logs for admin operations
   grep -i "topic" /var/log/kafka/server.log | grep -i "partition"
   ```

3. Review broker controller logs:
   ```bash
   grep -i "controller" /var/log/kafka/server.log | grep -i "<topic>"
   ```

4. Check for automated jobs or scripts that might modify topics:
   ```bash
   # Check for recent cron jobs
   grep -i "kafka" /var/log/cron
   ```

## Resolution Steps
1. Assess the impact:
   - For partition increases:
     - Consumer rebalancing will occur
     - Message ordering guarantees only apply within partitions
     - No data loss should occur

   - For partition decreases (rare and not recommended):
     - Data in removed partitions may be lost
     - Consumer rebalancing will occur
     - Applications relying on partition count may fail

2. If the change was unintentional:
   - For partition increases, you generally cannot revert safely
   - Document the new partition count for reference
   - Update any dependent applications that rely on specific partition counts

3. If the change is causing consumer problems:
   - Restart affected consumer groups to trigger clean rebalancing:
     ```bash
     # First check consumer group details
     kafka-consumer-groups.sh --bootstrap-server <kafka-bootstrap-servers> --describe --group <group-id>
     
     # Then reset offsets if needed
     kafka-consumer-groups.sh --bootstrap-server <kafka-bootstrap-servers> --group <group-id> --reset-offsets --to-latest --all-topics --execute
     ```

4. Prevent unauthorized changes:
   - Review and restrict Kafka ACLs for topic administration:
     ```bash
     kafka-acls.sh --bootstrap-server <kafka-bootstrap-servers> --add --allow-principal User:<user> --operation Create --topic <topic> --command-config admin.properties
     ```

## Prevention
1. Implement Change Management for Kafka:
   - Document all planned topic configuration changes
   - Require approval for topology changes
   - Use version-controlled topic configuration files

2. Configure appropriate ACLs:
   ```bash
   # Restrict who can alter topics
   kafka-acls.sh --bootstrap-server <kafka-bootstrap-servers> --add --allow-principal User:<admin-user> --operation Alter --topic <topic> --command-config admin.properties
   ```

3. Monitor topic configurations regularly:
   ```bash
   # Script to check and alert on topic configuration changes
   #!/bin/bash
   TOPICS=$(kafka-topics.sh --bootstrap-server <kafka-bootstrap-servers> --list)
   for TOPIC in $TOPICS; do
     PARTITIONS=$(kafka-topics.sh --bootstrap-server <kafka-bootstrap-servers> --describe --topic $TOPIC | grep -c "Partition:")
     echo "$TOPIC: $PARTITIONS partitions"
   done > /tmp/current_topic_config.txt
   ```

4. Document standard partition counts for all topics and validate against this baseline
