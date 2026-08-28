package com.eurosa.bank.paymentstatusservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "payment_status")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PaymentStatu {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
