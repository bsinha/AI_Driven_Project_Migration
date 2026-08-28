package com.eurosa.bank.customeridentityservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "customer-identity-service", "status", "UP");
    }

    @GetMapping("/customer_identity")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "customer-identity-service"));
    }

    @PostMapping("/customer_identity")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "customer-identity-service", "created", true);
    }
}
