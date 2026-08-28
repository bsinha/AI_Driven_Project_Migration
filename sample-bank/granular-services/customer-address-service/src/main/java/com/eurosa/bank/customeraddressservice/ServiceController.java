package com.eurosa.bank.customeraddressservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "customer-address-service", "status", "UP");
    }

    @GetMapping("/customer_address")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "customer-address-service"));
    }

    @PostMapping("/customer_address")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "customer-address-service", "created", true);
    }
}
