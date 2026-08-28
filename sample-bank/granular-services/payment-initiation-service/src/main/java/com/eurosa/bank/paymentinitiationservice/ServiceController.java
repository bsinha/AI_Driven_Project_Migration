package com.eurosa.bank.paymentinitiationservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "payment-initiation-service", "status", "UP");
    }

    @GetMapping("/payment_initiation")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "payment-initiation-service"));
    }

    @PostMapping("/payment_initiation")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "payment-initiation-service", "created", true);
    }
}
