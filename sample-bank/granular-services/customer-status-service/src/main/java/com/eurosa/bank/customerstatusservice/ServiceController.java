package com.eurosa.bank.customerstatusservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "customer-status-service", "status", "UP");
    }

    @GetMapping("/customer_status")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "customer-status-service"));
    }

    @PostMapping("/customer_status")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "customer-status-service", "created", true);
    }
}
