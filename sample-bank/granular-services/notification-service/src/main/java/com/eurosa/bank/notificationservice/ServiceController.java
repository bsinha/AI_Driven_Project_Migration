package com.eurosa.bank.notificationservice;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "notification-service", "status", "UP");
    }

    @GetMapping("/notification")
    public List<Map<String, Object>> list() {
        return List.of(Map.of("service", "notification-service"));
    }

    @PostMapping("/notification")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        return Map.of("service", "notification-service", "created", true);
    }
}
