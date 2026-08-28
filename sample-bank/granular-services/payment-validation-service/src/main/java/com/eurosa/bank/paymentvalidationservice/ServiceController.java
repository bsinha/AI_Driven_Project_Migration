package com.eurosa.bank.paymentvalidationservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "payment-validation-service", "status", "UP");
    }

    @GetMapping("/payment_validation")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "payment-validation-service"));
    }

    @PostMapping("/payment_validation")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "payment-validation-service", "created", true);
    }
}
