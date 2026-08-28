package com.eurosa.bank.accountrulesservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "account_rules")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AccountRule {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
