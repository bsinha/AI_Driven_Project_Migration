package com.eurosa.bank.accountlifecycleservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "account_lifecycle_events")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AccountLifecycleEvent {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
