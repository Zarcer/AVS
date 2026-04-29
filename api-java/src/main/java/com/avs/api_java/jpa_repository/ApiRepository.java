package com.avs.api_java.jpa_repository;

import com.avs.api_java.entity.RecordEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;

public interface ApiRepository extends JpaRepository<RecordEntity, Long> {
    @Query(value = """
        SELECT DISTINCT ON (sensor_id) *
        FROM sensors
        ORDER BY sensor_id, ts DESC
        """, nativeQuery = true)
    List<RecordEntity> getCurrent();

    @Query(value = """
        SELECT *
        FROM sensors
        WHERE sensor_id = :sensorId
          AND ts >= :from
          AND ts <= :to
        ORDER BY ts ASC
        """, nativeQuery = true)
    List<RecordEntity> getHistory(@Param("sensorId") String sensorId, @Param("from") Instant from, @Param("to") Instant to);

        @Query(value = """
        SELECT
            to_timestamp(floor(extract(epoch from ts) / :intervalSeconds) * :intervalSeconds) AS bucket,
            AVG(co2) AS co2,
            AVG(temperature) AS temperature,
            AVG(humidity) AS humidity
        FROM sensors
        WHERE sensor_id = :sensorId
          AND ts >= :from
          AND ts <= :to
        GROUP BY bucket
        ORDER BY bucket ASC
        """, nativeQuery = true)
    List<Object[]> getHistoryAggregated(
            @Param("sensorId") String sensorId,
            @Param("from") Instant from,
            @Param("to") Instant to,
            @Param("intervalSeconds") long intervalSeconds);
}
