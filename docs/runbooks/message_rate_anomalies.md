# Message Rate Anomalies Runbook

## Alert Description
This alert triggers when message production or consumption rates deviate significantly from normal patterns. Rate anomalies can indicate application issues, data flow problems, or potential security incidents.

## Potential Causes
- Application deployment changes
- Batch jobs starting or failing
- Upstream data source changes
- System or network performance issues
- Potential security incidents (unusual traffic patterns)
- Consumer or producer application failures

## Diagnostic Steps
1. Check message rates for affected topics:
   ```bash
   # Monitor production rate (run twice with interval to calculate rate)
   kafka-run-class.sh kafka.tools.GetOffsetShell --broker-list <kafka-bootstrap-servers> --topic <topic> --time -1
   
   # Monitor consumption rate
   kafka-consumer-groups.sh --bootstrap-server <kafka-bootstrap-servers> --describe --group <group-id>
   ```

2. Investigate application logs for producer/consumer applications

3. Check for recent deployments or changes:
   ```bash
   # Review deployment logs or CI/CD pipelines
   ```

4. Analyze message content for abnormalities (if possible):
   ```bash
   # Consume a sample of messages
   kafka-console-consumer.sh --bootstrap-server <kafka-bootstrap-servers> --topic <topic> --max-messages 10
   ```

5. Check system and network metrics for correlated anomalies

## Resolution Steps
1. For decreased production rates:
   - Check producer application health
   - Verify upstream data sources are available
   - Check for network or firewall issues between producers and Kafka
   - Restart producer applications if necessary

2. For increased production rates:
   - Determine if increase is expected (new feature, more users, etc.)
   - Check for duplicate message production or loops
   - Verify broker capacity can handle increased load
   - Consider throttling producers if necessary:
     ```properties
     # In producer config
     max.in.flight.requests.per.connection=1
     linger.ms=5
     ```

3. For decreased consumption rates:
   - Check consumer application health
   - Look for processing bottlenecks in consumer code
   - Verify downstream systems are functioning properly
   - Restart consumer applications if necessary

4. For unintended rate changes due to application issues:
   - Roll back recent deployments if they caused the issue
   - Fix application bugs causing rate anomalies
   - Implement gradual return to normal rates if sudden changes would cause issues

## Prevention
1. Implement proper rate monitoring:
   ```bash
   # Set up historical baselines for message rates
   ```

2. Configure alerting with appropriate thresholds:
   ```
   # Alert when rates deviate by more than 30% from baseline
   rate_change_threshold=0.3
   ```

3. Implement rate limiting in producers:
   ```properties
   # Configure producer quotas
   producer_byte_rate=10485760  # 10MB/s
   ```

4. Document expected rate patterns:
   - Catalog normal daily and weekly patterns
   - Document expected changes during known events (e.g., month-end processing)
