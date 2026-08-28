package com.eurosa.bank.riskassessmentservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "risk_scores")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RiskScore {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
