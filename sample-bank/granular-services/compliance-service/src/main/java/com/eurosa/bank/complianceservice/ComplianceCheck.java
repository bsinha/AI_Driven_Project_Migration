package com.eurosa.bank.complianceservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "compliance_checks")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ComplianceCheck {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
