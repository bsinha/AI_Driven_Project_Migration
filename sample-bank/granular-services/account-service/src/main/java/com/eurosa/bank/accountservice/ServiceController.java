package com.eurosa.bank.accountservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "account-service", "status", "UP");
    }

    @GetMapping("/account")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "account-service"));
    }

    @PostMapping("/account")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "account-service", "created", true);
    }
}
