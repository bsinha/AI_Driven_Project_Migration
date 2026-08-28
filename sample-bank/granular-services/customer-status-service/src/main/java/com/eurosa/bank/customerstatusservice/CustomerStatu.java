package com.eurosa.bank.customerstatusservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "customer_status")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerStatu {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
