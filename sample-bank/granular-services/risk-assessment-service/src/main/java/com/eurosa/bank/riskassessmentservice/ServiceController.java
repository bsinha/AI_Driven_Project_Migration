package com.eurosa.bank.riskassessmentservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "risk-assessment-service", "status", "UP");
    }

    @GetMapping("/risk_assessment")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "risk-assessment-service"));
    }

    @PostMapping("/risk_assessment")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "risk-assessment-service", "created", true);
    }
}
