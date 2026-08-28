package com.eurosa.bank.paymentexecutionservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "payment_executions")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PaymentExecution {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
