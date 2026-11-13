package telemetry.flink;

import org.apache.flink.api.common.eventtime.SerializableTimestampAssigner;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.java.tuple.Tuple4;
import org.apache.flink.types.Row;

/** Preserve admitted tuples and assign their validated measurement timestamp. */
public final class PartitionTime
        implements MapFunction<Tuple4<String, String, Long, String>,
                Tuple4<String, String, Long, String>>,
        SerializableTimestampAssigner<Tuple4<String, String, Long, String>> {
    private static final long serialVersionUID = 1L;

    @Override
    public Tuple4<String, String, Long, String> map(
            Tuple4<String, String, Long, String> value) {
        return value;
    }

    @Override
    public long extractTimestamp(
            Tuple4<String, String, Long, String> value, long previousTimestamp) {
        return value.f2;
    }

    /** Same key/value Row envelope as PyFlink DataStream.key_by, without IPC. */
    public static final class AddKey
            implements MapFunction<Tuple4<String, String, Long, String>, Row> {
        private static final long serialVersionUID = 1L;

        @Override
        public Row map(Tuple4<String, String, Long, String> value) {
            return Row.of(value.f0, value);
        }
    }
}
