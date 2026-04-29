package com.avs.api_java.dto;

import java.time.Instant;

public class AggregatedRecordDto {
    private Instant ts;   
    private Double co2;
    private Double temperature;
    private Double humidity;

    public AggregatedRecordDto() {}

    public Instant getTs() { return ts; }
    public void setTs(Instant ts) { this.ts = ts; }
    
    public Double getCo2() { return co2; }
    public void setCo2(Double co2) { this.co2 = co2; }

    public Double getTemperature() { return temperature; }
    public void setTemperature(Double temperature) { this.temperature = temperature; }

    public Double getHumidity() { return humidity; }
    public void setHumidity(Double humidity) { this.humidity = humidity; }
}