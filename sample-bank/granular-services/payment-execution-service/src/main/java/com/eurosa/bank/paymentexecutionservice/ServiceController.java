package com.eurosa.bank.paymentexecutionservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "payment-execution-service", "status", "UP");
    }

    @GetMapping("/payment_execution")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "payment-execution-service"));
    }

    @PostMapping("/payment_execution")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "payment-execution-service", "created", true);
    }
}
