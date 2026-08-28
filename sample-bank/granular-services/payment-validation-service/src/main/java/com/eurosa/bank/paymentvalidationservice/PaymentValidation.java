package com.eurosa.bank.paymentvalidationservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "payment_validations")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PaymentValidation {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
