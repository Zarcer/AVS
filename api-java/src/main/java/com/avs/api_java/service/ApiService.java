package com.avs.api_java.service;

import com.avs.api_java.dto.AggregatedRecordDto;
import com.avs.api_java.entity.RecordEntity;
import com.avs.api_java.jpa_repository.ApiRepository;
import com.avs.api_java.redis.CurrentStateRedisService;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class ApiService {
    private final ApiRepository repo;
    private final CurrentStateRedisService currentStateRedisService;

    public ApiService(ApiRepository repo, CurrentStateRedisService currentStateRedisService){
        this.repo=repo;
        this.currentStateRedisService = currentStateRedisService;
    }

    public List<RecordEntity> getCurrentState (){
        try {
            List<RecordEntity> fromRedis = currentStateRedisService.getCurrentState();
            if (!fromRedis.isEmpty()) {
                return fromRedis;
            }
        } catch (DataAccessException ignored) {
        }
        return repo.getCurrent();
    }

    public List<RecordEntity> getSensorHistory(String sensorId, Instant from, Instant to) {
        return repo.getHistory(sensorId, from, to);
    }

    public List<AggregatedRecordDto> getSensorHistoryAggregated(String sensorId, Instant from, Instant to, long intervalSeconds) {
        List<Object[]> rows = repo.getHistoryAggregated(sensorId, from, to, intervalSeconds);
        return rows.stream().map(row -> {
            AggregatedRecordDto dto = new AggregatedRecordDto();
            dto.setTs((Instant) row[0]);
            dto.setCo2(((Number) row[1]).doubleValue());  
            dto.setTemperature(((Number) row[2]).doubleValue()); 
            dto.setHumidity(((Number) row[3]).doubleValue());    
            return dto;
        }).collect(Collectors.toList());
    }
}
