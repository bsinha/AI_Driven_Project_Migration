package com.eurosa.bank.paymentstatusservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "payment-status-service", "status", "UP");
    }

    @GetMapping("/payment_status")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "payment-status-service"));
    }

    @PostMapping("/payment_status")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "payment-status-service", "created", true);
    }
}
