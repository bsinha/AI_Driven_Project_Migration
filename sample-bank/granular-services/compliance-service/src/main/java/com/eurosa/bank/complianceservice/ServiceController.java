package com.eurosa.bank.complianceservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "compliance-service", "status", "UP");
    }

    @GetMapping("/compliance")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "compliance-service"));
    }

    @PostMapping("/compliance")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "compliance-service", "created", true);
    }
}
