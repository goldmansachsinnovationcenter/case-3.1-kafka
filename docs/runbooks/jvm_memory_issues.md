# JVM Memory Issues Runbook

## Alert Description
This alert triggers when Kafka broker JVMs show signs of memory pressure, including high heap usage, frequent garbage collection, or long GC pauses. JVM memory issues can lead to broker performance degradation or outages.

## Potential Causes
- Undersized heap allocation
- Memory leaks
- High message traffic
- Large message sizes
- Inefficient broker configurations
- Excessive metadata due to many topics/partitions
- JVM garbage collection issues

## Diagnostic Steps
1. Check JVM heap usage:
   ```bash
   # Using JMX
   kafka-run-class.sh kafka.tools.JmxTool --object-name java.lang:type=Memory --attributes HeapMemoryUsage --jmx-url service:jmx:rmi:///jndi/rmi://<broker-host>:9999/jmxrmi
   ```

2. Monitor garbage collection statistics:
   ```bash
   # Using JMX
   kafka-run-class.sh kafka.tools.JmxTool --object-name java.lang:type=GarbageCollector,name=* --jmx-url service:jmx:rmi:///jndi/rmi://<broker-host>:9999/jmxrmi
   ```

3. Check for excessive GC in logs:
   ```bash
   grep -i "gc" /var/log/kafka/server.log
   ```

4. Review broker load and resource usage:
   ```bash
   # Check CPU, memory, disk IO
   top -bn1
   iostat -x 1 10
   ```

## Resolution Steps
1. For high heap usage:
   - Increase heap size if hardware allows:
     ```bash
     # Edit /etc/kafka/jvm.options or equivalent
     -Xms6g
     -Xmx6g
     ```
   - Restart broker after changes:
     ```bash
     systemctl restart kafka
     ```

2. For frequent GC or long GC pauses:
   - Tune garbage collection settings:
     ```bash
     # Add to JVM options
     -XX:+UseG1GC
     -XX:MaxGCPauseMillis=20
     -XX:InitiatingHeapOccupancyPercent=35
     -XX:+ExplicitGCInvokesConcurrent
     ```

3. For memory leaks or gradual memory growth:
   - Take heap dumps for analysis:
     ```bash
     jmap -dump:format=b,file=/tmp/heapdump.bin <kafka-pid>
     ```
   - Update to latest Kafka version to fix known memory issues
   - Restart broker if immediate relief is needed:
     ```bash
     systemctl restart kafka
     ```

4. For excessive metadata due to many topics/partitions:
   - Consider cleaning up unused topics:
     ```bash
     kafka-topics.sh --bootstrap-server <kafka-bootstrap-servers> --delete --topic <unused-topic>
     ```
   - Optimize server.properties for large topic counts:
     ```properties
     # Metadata cache settings
     replica.socket.receive.buffer.bytes=65536
     num.replica.fetchers=4
     ```

## Prevention
1. Configure appropriate JVM settings:
   ```bash
   # Recommended settings for production
   -Xms4g
   -Xmx4g
   -XX:MetaspaceSize=96m
   -XX:+UseG1GC
   -XX:MaxGCPauseMillis=20
   -XX:InitiatingHeapOccupancyPercent=35
   -XX:G1HeapRegionSize=16M
   -XX:MinMetaspaceFreeRatio=50
   -XX:MaxMetaspaceFreeRatio=80
   ```

2. Implement proper monitoring:
   - Monitor heap usage over time
   - Track GC frequency and duration
   - Alert on sustained high memory usage

3. Scale appropriately:
   - Add brokers to distribute load
   - Limit topics and partitions per broker based on available memory
   - Consider dedicated brokers for high-throughput topics

4. Perform regular broker maintenance:
   - Schedule periodic restarts during low-traffic periods
   - Upgrade Kafka regularly to benefit from memory optimizations
