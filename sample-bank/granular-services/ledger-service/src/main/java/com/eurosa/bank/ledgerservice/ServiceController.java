package com.eurosa.bank.ledgerservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "ledger-service", "status", "UP");
    }

    @GetMapping("/ledger")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "ledger-service"));
    }

    @PostMapping("/ledger")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "ledger-service", "created", true);
    }
}
