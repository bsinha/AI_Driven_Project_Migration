package com.eurosa.bank.accountlifecycleservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "account-lifecycle-service", "status", "UP");
    }

    @GetMapping("/account_lifecycle")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "account-lifecycle-service"));
    }

    @PostMapping("/account_lifecycle")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "account-lifecycle-service", "created", true);
    }
}
