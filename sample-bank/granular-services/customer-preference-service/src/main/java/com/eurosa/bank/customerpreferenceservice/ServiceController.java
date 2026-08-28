package com.eurosa.bank.customerpreferenceservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "customer-preference-service", "status", "UP");
    }

    @GetMapping("/customer_preference")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "customer-preference-service"));
    }

    @PostMapping("/customer_preference")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "customer-preference-service", "created", true);
    }
}
